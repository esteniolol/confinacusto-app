"""
Motor de cálculo do ConfinaCusto.

O sistema trabalha com um PROJETO (um dicionário simples, salvo em JSON) que guarda tudo o que
é cadastrado nas telas: fazenda, currais, lote e desempenho, compra e venda, dieta, custos
operacionais, combustível, investimento e vendas. A partir do projeto o motor monta a "Base" e
recalcula COE → COT → CT, DRE, fluxo de caixa, VPL/TIR e Monte Carlo — a mesma lógica da planilha.

Todas as contas aceitam números ou arrays do numpy (para simular milhares de cenários de uma vez).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace

import numpy as np

# ----------------------------------------------------------------------------
# Catálogos usados pelas telas
# ----------------------------------------------------------------------------
GRUPOS = ["Sanidade", "Mão de obra", "Combustível", "Energia", "Manutenção", "Assistência técnica",
          "Administração", "Outros"]
BASES = {
    "fixo": "Valor no ano",
    "cab": "Por boi que entra",
    "cabdia": "Por cabeça-dia",
    "pct_bens": "% do valor dos bens",
    "pct_folha": "% sobre a folha",
}
SISTEMAS = ["Confinamento a céu aberto", "Confinamento coberto (galpão)", "Semiconfinamento",
            "Terminação intensiva a pasto (TIP)"]
REPOSICAO = ["Compra de boi magro", "Recria própria", "Misto"]
REGIMES = ["Produtor rural PF", "Pessoa jurídica"]

# chave, rótulo, unidade, tipo ("int", "num", "pct"), ajuda
PREMISSAS_LOTE = [
    ("cab", "Bois confinados por ciclo", "cab", "int", "Total de animais que passam pelo cocho em cada ciclo/giro."),
    ("ciclos", "Ciclos (giros) por ano", "ciclos", "int", None),
    ("dias", "Dias de cocho por ciclo", "dias", "int", "Média de dias que cada boi fica no confinamento."),
    ("dias_ano", "Dias de operação no ano", "dias", "int", "Dias em que há trato (da primeira entrada à última saída)."),
    ("pe", "Peso vivo de entrada", "kg", "num", None),
    ("gmd", "Ganho médio diário (GMD)", "kg/dia", "num", None),
    ("rc", "Rendimento de carcaça na saída", "%", "pct", None),
    ("rc0", "Rendimento de carcaça na entrada (referência)", "%", "pct",
     "Convenção para calcular @ produzidas. O padrão de mercado é 50%."),
    ("mort", "Mortalidade no ciclo", "%", "pct", None),
    ("cms", "Consumo de matéria seca", "% do PV", "pct", "Consumo diário de MS em % do peso vivo médio."),
]
PREMISSAS_MERCADO = [
    ("vcompra", "Valor de compra do boi magro", "R$/cab", "num", "Se a reposição é própria, use o valor de mercado."),
    ("frete", "Frete de compra", "R$/cab", "num", None),
    ("outros_aq", "Outros custos de aquisição", "R$/cab", "num", "Comissão, GTA, exames de entrada…"),
    ("pasto", "Custo pré-confinamento a pasto", "R$/cab", "num", "Período entre a compra e a entrada no cocho."),
    ("pvenda", "Preço de venda do boi gordo", "R$/@", "num", None),
    ("funrural", "Funrural + Senar sobre a venda", "%", "pct", "Produtor PF: 1,2% + 0,1% RAT + 0,2% Senar = 1,5%."),
    ("tma", "Taxa mínima de atratividade (TMA)", "% a.a.", "pct", "Custo de oportunidade do capital (ex.: Selic/CDI)."),
]
CHAVES_PREMISSAS = [k for k, *_ in PREMISSAS_LOTE + PREMISSAS_MERCADO] + ["cap"]


# ----------------------------------------------------------------------------
# Projeto
# ----------------------------------------------------------------------------
def projeto_em_branco() -> dict:
    return {
        "versao": 1,
        "fazenda": {"nome": "", "municipio": "", "uf": "", "responsavel": "", "ciclo": "",
                    "sistema": SISTEMAS[0], "reposicao": REPOSICAO[0], "regime": REGIMES[0]},
        "premissas": {"cab": 0, "ciclos": 1, "dias": 0, "dias_ano": 0, "pe": 0.0, "gmd": 0.0, "rc": 0.0,
                      "rc0": 0.50, "mort": 0.0, "cms": 0.0, "vcompra": 0.0, "frete": 0.0, "outros_aq": 0.0,
                      "pasto": 0.0, "pvenda": 0.0, "funrural": 0.015, "tma": 0.12, "cap": 0},
        "currais": [],
        "dieta": [],
        "custos": [
            {"item": "Sanidade (vacinas, vermífugo, medicamentos)", "grupo": "Sanidade", "classe": "Variável",
             "base": "cab", "quantidade": 1, "valor_unit": 0.0, "multiplicador": 1, "rateio": 1},
            {"item": "Equipe do confinamento (salários)", "grupo": "Mão de obra", "classe": "Fixo",
             "base": "fixo", "quantidade": 0, "valor_unit": 0.0, "multiplicador": 13.33, "rateio": 1},
            {"item": "Encargos sobre a folha (FGTS)", "grupo": "Mão de obra", "classe": "Fixo",
             "base": "pct_folha", "quantidade": 1, "valor_unit": 0.08, "multiplicador": 1, "rateio": 1},
            {"item": "Energia elétrica", "grupo": "Energia", "classe": "Fixo",
             "base": "fixo", "quantidade": 1, "valor_unit": 0.0, "multiplicador": 12, "rateio": 1},
            {"item": "Manutenção de instalações e máquinas", "grupo": "Manutenção", "classe": "Fixo",
             "base": "pct_bens", "quantidade": 1, "valor_unit": 0.03, "multiplicador": 1, "rateio": 1},
            {"item": "Assistência técnica / nutricionista", "grupo": "Assistência técnica", "classe": "Fixo",
             "base": "fixo", "quantidade": 1, "valor_unit": 0.0, "multiplicador": 12, "rateio": 1},
            {"item": "Despesas administrativas (rateadas)", "grupo": "Administração", "classe": "Fixo",
             "base": "fixo", "quantidade": 1, "valor_unit": 0.0, "multiplicador": 12, "rateio": 1},
        ],
        "combustivel": {"preco_diesel": 0.0, "coef": 0.243, "carga_batida": 5.0, "min_carga": 15,
                        "min_mistura": 10, "min_distrib": 25, "km_dia": 0, "km_l": 10.0, "preco_gasolina": 0.0,
                        "maquinas": [{"maquina": "Trator no misturador", "cv": 100, "fator": 1.0, "horas_dia": 0.0}]},
        "investimento": [],
        "vendas": [],
    }


def copiar(projeto: dict) -> dict:
    return copy.deepcopy(projeto)


def _f(v, padrao=0.0) -> float:
    try:
        x = float(v)
        return padrao if np.isnan(x) else x
    except (TypeError, ValueError):
        return padrao


def capacidade_total(projeto: dict) -> float:
    return sum(_f(c.get("capacidade")) for c in projeto.get("currais", []))


# ----------------------------------------------------------------------------
# Cálculos auxiliares do projeto (usados pelas telas de cadastro e pelo motor)
# ----------------------------------------------------------------------------
def _div(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.asarray(a, dtype=float) / np.asarray(b, dtype=float)
    r = np.where(np.isfinite(r), r, 0.0)
    return float(r) if r.ndim == 0 else r


def derivados(p: dict) -> dict:
    """Pesos, arrobas e cabeças a partir das premissas (sem custos)."""
    cab_ent = p["cab"] * p["ciclos"]
    ps = p["pe"] + p["gmd"] * p["dias"]
    pmed = (p["pe"] + ps) / 2
    return dict(
        cab_ent=cab_ent,
        cab_vend=cab_ent * (1 - p["mort"]),
        cab_dia=p["cab"] * p["dias"] * p["ciclos"] * (1 - p["mort"] / 2),
        ps=ps, pmed=pmed,
        arr_sai=ps * p["rc"] / 15,
        arr_prod=(ps * p["rc"] - p["pe"] * p["rc0"]) / 15,
        cms_kg=p["cms"] * pmed,
    )


def resumo_dieta(dieta: list[dict]) -> dict:
    validos = [i for i in dieta if _f(i.get("ms")) > 0 and _f(i.get("inclusao")) > 0]
    inc = sum(_f(i["inclusao"]) for i in validos)
    custo_t_ms = sum(_f(i["inclusao"]) * _f(i.get("preco_t")) / _f(i["ms"]) for i in validos)
    mn_por_ms = sum(_f(i["inclusao"]) / _f(i["ms"]) for i in validos)   # kg MN por kg MS
    return dict(inclusao_total=inc, custo_kg_ms=custo_t_ms / 1000, mn_por_ms=mn_por_ms, n=len(validos))


def resumo_combustivel(projeto: dict) -> dict:
    p = projeto["premissas"]
    cb = projeto["combustivel"]
    d = derivados(p)
    dieta = resumo_dieta(projeto["dieta"])
    dias_ano = _f(p.get("dias_ano"))
    t_mn_ano = d["cms_kg"] * d["cab_dia"] * dieta["mn_por_ms"] / 1000
    mn_dia = _div(t_mn_ano, dias_ano)
    batidas = float(np.ceil(_div(mn_dia, _f(cb.get("carga_batida"))))) if mn_dia else 0.0
    maquinas = []
    litros = 0.0
    for m in cb.get("maquinas", []):
        lph = _f(m.get("cv")) * 0.736 * _f(cb.get("coef")) * _f(m.get("fator"))
        l_ano = lph * _f(m.get("horas_dia")) * dias_ano
        litros += l_ano
        maquinas.append({**m, "l_h": lph, "litros_ano": l_ano})
    gas = _div(_f(cb.get("km_dia")), _f(cb.get("km_l"))) * dias_ano
    total = litros * _f(cb.get("preco_diesel")) + gas * _f(cb.get("preco_gasolina"))
    return dict(t_mn_ano=t_mn_ano, mn_dia=mn_dia, batidas=batidas, maquinas=maquinas, litros_diesel=litros,
                litros_gasolina=gas, custo_ano=total, l_por_t=_div(litros, t_mn_ano),
                horas_sugeridas={
                    "misturador": batidas * (_f(cb.get("min_carga")) + _f(cb.get("min_mistura"))) / 60,
                    "distribuidor": batidas * _f(cb.get("min_distrib")) / 60,
                    "pa": batidas * _f(cb.get("min_carga")) / 60,
                })


def resumo_investimento(itens: list[dict]) -> dict:
    linhas, valor, dep, desemb, resid = [], 0.0, 0.0, 0.0, 0.0
    for it in itens:
        total = _f(it.get("quantidade")) * _f(it.get("valor_unit"))
        atrib = total * _f(it.get("uso"), 1.0)
        vida = _f(it.get("vida"))
        res = _f(it.get("residual"))
        d = atrib * (1 - res) / vida if vida > 0 else 0.0
        inc = 1.0 if it.get("incluir", True) in (True, 1, "1", "Sim", "sim") else 0.0
        linhas.append({**it, "valor_total": total, "valor_atribuido": atrib, "depreciacao": d,
                       "valor_residual": atrib * res})
        valor += atrib
        dep += d
        desemb += atrib * inc
        resid += atrib * res * inc
    return dict(linhas=linhas, valor_bens=valor, depreciacao=dep, desembolso=desemb, residual=resid)


def valor_anual_custos(projeto: dict, valor_bens: float | None = None) -> list[dict]:
    """Custo anual de cada linha de custo operacional, com as premissas atuais (para exibição)."""
    p = projeto["premissas"]
    d = derivados(p)
    if valor_bens is None:
        valor_bens = resumo_investimento(projeto["investimento"])["valor_bens"]
    drivers = {"fixo": 1.0, "cab": d["cab_ent"], "cabdia": d["cab_dia"], "pct_bens": valor_bens}
    out = []
    for c in projeto["custos"]:
        unit = _f(c.get("quantidade"), 1.0) * _f(c.get("valor_unit")) * _f(c.get("multiplicador"), 1.0) * \
            _f(c.get("rateio"), 1.0)
        out.append({**c, "_unit": unit, "anual": unit * drivers.get(c.get("base", "fixo"), 1.0)
                    if c.get("base") != "pct_folha" else None})
    folha = sum(o["anual"] for o in out if o.get("grupo") == "Mão de obra" and o["anual"] is not None)
    for o in out:
        if o.get("base") == "pct_folha":
            o["anual"] = o["_unit"] * folha
    return out


# ----------------------------------------------------------------------------
# Validação (o que falta para o sistema conseguir calcular)
# ----------------------------------------------------------------------------
def validar(projeto: dict) -> dict[str, list[str]]:
    p = projeto["premissas"]
    pend = {"Fazenda": [], "Currais": [], "Lote e desempenho": [], "Compra e venda": [], "Dieta": [],
            "Custos operacionais": [], "Combustível": [], "Investimento": [], "Vendas": []}
    if not projeto["fazenda"].get("nome"):
        pend["Fazenda"].append("Informe o nome da fazenda.")
    if not projeto["currais"]:
        pend["Currais"].append("Cadastre pelo menos um curral.")
    for k, rot in (("cab", "bois por ciclo"), ("ciclos", "ciclos por ano"), ("dias", "dias de cocho"),
                   ("pe", "peso de entrada"), ("gmd", "GMD"), ("rc", "rendimento de carcaça"),
                   ("cms", "consumo de MS")):
        if _f(p.get(k)) <= 0:
            pend["Lote e desempenho"].append(f"Informe {rot}.")
    if _f(p.get("dias_ano")) < _f(p.get("dias")):
        pend["Lote e desempenho"].append("Dias de operação no ano menor que os dias de cocho.")
    for k, rot in (("vcompra", "valor de compra do boi magro"), ("pvenda", "preço de venda da @")):
        if _f(p.get(k)) <= 0:
            pend["Compra e venda"].append(f"Informe {rot}.")
    rd = resumo_dieta(projeto["dieta"])
    if rd["n"] == 0:
        pend["Dieta"].append("Cadastre os ingredientes da dieta.")
    elif abs(rd["inclusao_total"] - 1) > 0.005:
        pend["Dieta"].append(f"A inclusão soma {rd['inclusao_total'] * 100:.1f}% — precisa somar 100%.")
    if not projeto["investimento"]:
        pend["Investimento"].append("Sem instalações e máquinas: o projeto fica sem depreciação e sem investimento.")
    return pend


BLOQUEIAM = ("Lote e desempenho", "Compra e venda", "Dieta")


def pode_calcular(pend: dict) -> bool:
    return all(not pend[k] for k in BLOQUEIAM)


# ----------------------------------------------------------------------------
# Base de cálculo
# ----------------------------------------------------------------------------
@dataclass
class Ingrediente:
    nome: str
    ms: float
    inclusao: float
    preco_t: float

    @property
    def eh_milho(self) -> bool:
        n = self.nome.lower()
        return "milho" in n and "silagem" not in n


@dataclass
class LinhaCusto:
    item: str
    grupo: str
    classe: str        # "Fixo" ou "Variável"
    base: str          # "fixo", "cab", "cabdia", "pct_bens"
    valor: float       # valor por unidade da base, já anual


@dataclass
class Base:
    p: dict
    dieta: list
    custos: list
    valor_bens: float
    depreciacao: float
    desembolso_ano0: float
    residual: float
    fonte: str = ""
    excel: dict = field(default_factory=dict)


def base_de_projeto(projeto: dict) -> Base:
    p = {k: _f(projeto["premissas"].get(k)) for k in CHAVES_PREMISSAS}
    if p["ciclos"] <= 0:
        p["ciclos"] = 1.0
    dieta = [Ingrediente(str(i.get("ingrediente", "")), _f(i["ms"]), _f(i["inclusao"]), _f(i.get("preco_t")))
             for i in projeto["dieta"] if _f(i.get("ms")) > 0 and _f(i.get("inclusao")) > 0]
    inv = resumo_investimento(projeto["investimento"])
    d = derivados(p)

    custos = []
    for c in valor_anual_custos(projeto, inv["valor_bens"]):
        base = c.get("base", "fixo")
        if base == "pct_folha":              # encargos: valor fixo no ano, calculado sobre a folha
            base, valor = "fixo", c["anual"]
        else:
            valor = c["_unit"]
        custos.append(LinhaCusto(str(c.get("item", "")), c.get("grupo") or "Outros", c.get("classe") or "Fixo",
                                 base, valor))
    comb = resumo_combustivel(projeto)["custo_ano"]
    if comb:
        custos.append(LinhaCusto("Combustível (diesel e gasolina)", "Combustível", "Variável", "cabdia",
                                 _div(comb, d["cab_dia"])))
    return Base(p, dieta, custos, inv["valor_bens"], inv["depreciacao"], inv["desembolso"], inv["residual"],
                fonte=projeto["fazenda"].get("nome", ""))


# ----------------------------------------------------------------------------
# Cenário do simulador
# ----------------------------------------------------------------------------
@dataclass
class Cenario:
    pvenda: float | np.ndarray | None = None
    vcompra: float | np.ndarray | None = None
    fator_milho: float | np.ndarray = 1.0
    gmd: float | np.ndarray | None = None
    dias: float | np.ndarray | None = None
    mort: float | np.ndarray | None = None
    cab: float | np.ndarray | None = None
    tma: float | None = None


def calcular(base: Base, cen: Cenario | None = None) -> dict:
    cen = cen or Cenario()
    p = dict(base.p)
    for k in ("pvenda", "vcompra", "gmd", "dias", "mort", "cab", "tma"):
        v = getattr(cen, k)
        if v is not None:
            p[k] = v
    d = derivados(p)
    cab_ent, cab_vend, cab_dia = d["cab_ent"], d["cab_vend"], d["cab_dia"]

    custo_kg_ms = sum(i.inclusao * i.preco_t * (cen.fator_milho if i.eh_milho else 1.0) / i.ms
                      for i in base.dieta) / 1000
    receita = cab_vend * d["arr_sai"] * p["pvenda"]
    c = {
        "rep": cab_ent * p["vcompra"],
        "aq": cab_ent * (p["frete"] + p["outros_aq"]),
        "pasto": cab_ent * p["pasto"],
        "alim": custo_kg_ms * d["cms_kg"] * cab_dia,
        "fun": receita * p["funrural"],
    }
    drivers = {"fixo": 1.0, "cab": cab_ent, "cabdia": cab_dia, "pct_bens": base.valor_bens}
    por_grupo, linhas, var_l, fix_l = {}, [], 0.0, 0.0
    for lc in base.custos:
        v = lc.valor * drivers.get(lc.base, 1.0)
        por_grupo[lc.grupo] = por_grupo.get(lc.grupo, 0.0) + v
        linhas.append((lc, v))
        if lc.classe == "Variável":
            var_l = var_l + v
        else:
            fix_l = fix_l + v
    c["sanid"] = por_grupo.get("Sanidade", 0.0)
    c["comb"] = por_grupo.get("Combustível", 0.0)

    coe = c["rep"] + c["aq"] + c["pasto"] + c["alim"] + c["fun"] + var_l + fix_l
    dep = base.depreciacao
    cot = coe + dep
    op_inv = base.valor_bens * p["tma"]
    op_giro = coe * p["tma"] * p["dias"] / 365
    ct = cot + op_inv + op_giro
    var = c["rep"] + c["aq"] + c["pasto"] + c["alim"] + c["fun"] + var_l + op_giro
    fix = fix_l + dep + op_inv

    res_op = receita - coe
    av = cab_vend * d["arr_sai"]
    ap = cab_vend * d["arr_prod"]
    sem_rep = c["rep"] + c["aq"]

    out = dict(
        p=p, **d, custo_kg_ms=custo_kg_ms, receita=receita, custos=c, por_grupo=por_grupo, linhas=linhas,
        fixos=fix_l, var_linhas=var_l, mao_de_obra=por_grupo.get("Mão de obra", 0.0),
        coe=coe, dep=dep, cot=cot, op_inv=op_inv, op_giro=op_giro, ct=ct, var=var, fix=fix,
        res_op=res_op, lucro=res_op - dep, lucro_econ=receita - ct,
        res_op_cab=_div(res_op, cab_vend), lucro_cab=_div(res_op - dep, cab_vend),
        pe_coe=_div(coe, av), pe_cot=_div(cot, av), pe_ct=_div(ct, av),
        cprod_mb=_div(c["pasto"] + c["alim"] + c["sanid"], ap),
        cprod_coe=_div(coe - sem_rep, ap),
        cprod_ct=_div(ct - sem_rep, ap),
        diaria_op=_div(coe - c["rep"] - c["aq"] - c["pasto"] - c["fun"], cab_dia),
        diaria_alim=_div(c["alim"], cab_dia),
        mc_cab=_div(receita - var, cab_vend),
    )
    out["ponto_eq_cab"] = _div(fix, out["mc_cab"])
    out["margem_seg"] = _div(p["pvenda"] - out["pe_ct"], p["pvenda"])
    out.update(viabilidade(base, out, p))
    return out


# ----------------------------------------------------------------------------
# Viabilidade
# ----------------------------------------------------------------------------
def _vpl(taxa, fluxos):
    return sum(f / (1 + taxa) ** t for t, f in enumerate(fluxos))


def _tir(fluxos, lo=-0.99, hi=5.0, it=200):
    f_lo, f_hi = _vpl(lo, fluxos), _vpl(hi, fluxos)
    if np.sign(f_lo) == np.sign(f_hi):
        return None
    for _ in range(it):
        mid = (lo + hi) / 2
        f_mid = _vpl(mid, fluxos)
        if np.sign(f_mid) == np.sign(f_lo):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def _payback(fluxos):
    acum = 0.0
    for t, f in enumerate(fluxos):
        ant = acum
        acum += f
        if t > 0 and ant < 0 <= acum:
            return (t - 1) + (-ant) / f
    return None


def viabilidade(base: Base, r: dict, p: dict, anos: int = 10) -> dict:
    if np.ndim(r["res_op"]) > 0:
        return {}
    giro = r["coe"] / p["ciclos"]
    fluxos = [-base.desembolso_ano0 - giro] + [r["res_op"]] * anos
    fluxos[-1] += giro + base.residual
    tma = p["tma"]
    desc = [f / (1 + tma) ** t for t, f in enumerate(fluxos)]
    return dict(fluxos=fluxos, fluxos_desc=desc, giro=giro, vpl=_vpl(tma, fluxos), tir=_tir(fluxos),
                payback=_payback(fluxos), payback_desc=_payback(desc),
                payback_fixo=base.desembolso_ano0 / r["res_op"] if r["res_op"] > 0 else None)


# ----------------------------------------------------------------------------
# Risco
# ----------------------------------------------------------------------------
def monte_carlo(base: Base, cen: Cenario, n: int = 5000, sd_venda=0.08, sd_compra=0.06,
                sd_milho=0.12, sd_gmd=0.08, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    p0 = calcular(base, cen)["p"]
    pv = p0["pvenda"] * (1 + rng.normal(0, sd_venda, n))
    vc = p0["vcompra"] * (1 + rng.normal(0, sd_compra, n))
    fm = cen.fator_milho * np.clip(1 + rng.normal(0, sd_milho, n), 0.3, None)
    gm = np.clip(p0["gmd"] * (1 + rng.normal(0, sd_gmd, n)), 0.3, None)
    res = np.asarray(calcular(base, replace(cen, pvenda=pv, vcompra=vc, fator_milho=fm, gmd=gm))["res_op_cab"])
    return dict(res_cab=res, prob_prejuizo=float((res < 0).mean()), p5=float(np.percentile(res, 5)),
                p50=float(np.percentile(res, 50)), p95=float(np.percentile(res, 95)), media=float(res.mean()))


def tornado(base: Base, cen: Cenario, var: float = 0.10) -> list[tuple[str, float, float]]:
    p0 = calcular(base, cen)["p"]
    fatores = [("Preço de venda (@)", "pvenda", p0["pvenda"]),
               ("Valor de compra do boi magro", "vcompra", p0["vcompra"]),
               ("GMD", "gmd", p0["gmd"]),
               ("Preço do milho", "fator_milho", cen.fator_milho),
               ("Dias de cocho", "dias", p0["dias"])]
    out = []
    for nome, k, v in fatores:
        lo = calcular(base, replace(cen, **{k: v * (1 - var)}))["res_op_cab"]
        hi = calcular(base, replace(cen, **{k: v * (1 + var)}))["res_op_cab"]
        out.append((nome, float(lo), float(hi)))
    return sorted(out, key=lambda x: abs(x[2] - x[1]))
