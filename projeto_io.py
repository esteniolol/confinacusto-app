"""Abrir, salvar e importar projetos (JSON do sistema ou planilha no formato da ferramenta)."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import openpyxl
import pandas as pd

from engine import _f, projeto_em_branco

DADOS = Path(__file__).parent / "dados"

PREMISSAS_EXCEL = {
    "cap": "Capacidade estática", "cab": "Bois confinados por ciclo", "ciclos": "Ciclos por ano",
    "dias_ano": "Dias de operação do confinamento", "dias": "Dias de cocho por ciclo",
    "pe": "Peso vivo de entrada", "gmd": "Ganho médio diário", "rc": "Rendimento de carcaça na saída",
    "rc0": "Rendimento de carcaça na entrada", "mort": "Mortalidade", "cms": "Consumo de matéria seca",
    "vcompra": "Valor de compra do boi magro", "frete": "Frete de compra", "outros_aq": "Outros custos de aquisição",
    "pasto": "Custo pré-confinamento a pasto", "pvenda": "Preço de venda do boi gordo", "funrural": "Funrural",
    "tma": "Taxa mínima de atratividade",
}


def _row(ws, prefix, col=1, start=1):
    for r in range(start, ws.max_row + 1):
        v = ws.cell(row=r, column=col).value
        if isinstance(v, str) and v.strip().startswith(prefix):
            return r
    return None


def _vendas_da_planilha(ws, ano: int | None = None) -> list[dict]:
    """Lê a tabela 'VENDAS DO CICLO' da aba Dados_Reais (linhas 'dd/mm · comprador')."""
    ini = _row(ws, "VENDAS DO CICLO")
    if not ini:
        return []
    ano = ano or dt.date.today().year
    vendas = []
    for r in range(ini + 2, ini + 200):
        rot = ws.cell(row=r, column=1).value
        if not rot or str(rot).upper().startswith("TOTAL"):
            break
        m = re.match(r"\s*(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\s*[·\-]?\s*(.*)", str(rot))
        if not m:
            continue
        d, mes, a, comp = m.groups()
        a = int(a) + (2000 if a and len(a) == 2 else 0) if a else ano
        n, pc = _f(ws.cell(row=r, column=2).value), _f(ws.cell(row=r, column=3).value)
        rend, pr = _f(ws.cell(row=r, column=5).value), _f(ws.cell(row=r, column=6).value)
        vendas.append({"data": str(dt.date(a, int(mes), int(d))), "comprador": comp.strip(), "animais": n,
                       "peso_vivo": pc / rend if rend else 0.0, "peso_carcaca": pc, "rendimento": rend,
                       "preco_arroba": pr, "valor_total": n * pc / 15 * pr})
    return vendas


def projeto_de_excel(arquivo, currais_csv=None, vendas_csv=None) -> tuple[dict, dict]:
    """Converte a planilha da ferramenta em projeto. Retorna (projeto, valores_calculados_no_excel)."""
    wb = openpyxl.load_workbook(arquivo, data_only=True)
    pj = projeto_em_branco()

    pr = wb["Premissas"]
    for k, pref in PREMISSAS_EXCEL.items():
        r = _row(pr, pref)
        if r:
            pj["premissas"][k] = _f(pr.cell(row=r, column=2).value)

    di = wb["Dieta"]
    pj["dieta"] = []
    for r in range(5, (_row(di, "TOTAL DA DIETA") or 13)):
        nome = di.cell(row=r, column=1).value
        if nome and _f(di.cell(row=r, column=3).value) > 0:
            pj["dieta"].append({"ingrediente": str(nome), "ms": _f(di.cell(row=r, column=2).value),
                                "inclusao": _f(di.cell(row=r, column=3).value),
                                "preco_t": _f(di.cell(row=r, column=4).value)})

    co = wb["Custos_Operacionais"]
    pj["custos"] = []
    r_tot = _row(co, "TOTAL") or 19
    preco_diesel = preco_gas = 0.0
    for r in range(5, r_tot):
        item = co.cell(row=r, column=1).value
        if not item:
            continue
        item = str(item)
        classe = str(co.cell(row=r, column=2).value or "Fixo")
        q, vu, mult, rat = (_f(co.cell(row=r, column=c).value) for c in (4, 5, 6, 7))
        linha = {"item": item, "classe": classe, "quantidade": q, "valor_unit": vu, "multiplicador": mult or 1,
                 "rateio": rat if rat else 1}
        if item.startswith("Diesel"):
            preco_diesel = vu
            continue
        if item.startswith("Gasolina"):
            preco_gas = vu
            continue
        if item.startswith("Sanidade"):
            linha.update(grupo="Sanidade", base="cab", quantidade=1)
        elif item.startswith(("Equipe", "Escritório")):
            linha.update(grupo="Mão de obra", base="fixo")
        elif item.startswith("Encargos"):
            linha.update(grupo="Mão de obra", base="pct_folha", quantidade=1)
        elif item.startswith("Energia"):
            linha.update(grupo="Energia", base="fixo")
        elif item.startswith("Manutenção"):
            linha.update(grupo="Manutenção", base="pct_bens", quantidade=1)
        elif item.startswith("Assistência"):
            linha.update(grupo="Assistência técnica", base="fixo")
        elif item.startswith("Outras despesas"):
            linha.update(grupo="Administração", base="fixo")
        elif item.startswith("Outros (EPI"):
            linha.update(grupo="Outros", base="cab", quantidade=1)
        else:
            linha.update(grupo="Outros", base="fixo")
        pj["custos"].append(linha)

    cb = pj["combustivel"]
    cb.update(preco_diesel=preco_diesel, preco_gasolina=preco_gas)
    for k, pref in (("coef", "Coeficiente de consumo"), ("carga_batida", "Carga do misturador"),
                    ("min_carga", "Minutos por batida — carregamento"), ("min_mistura", "Minutos por batida — mistura"),
                    ("min_distrib", "Minutos por batida — distribuição"), ("km_dia", "Saveiro — km"),
                    ("km_l", "Saveiro — consumo")):
        r = _row(co, pref)
        if r:
            cb[k] = _f(co.cell(row=r, column=4).value)
    r_h = _row(co, "Máquina / operação")
    r_t = _row(co, "TOTAL DE DIESEL")
    if r_h and r_t:
        cb["maquinas"] = []
        for r in range(r_h + 1, r_t):
            nome = co.cell(row=r, column=1).value
            if nome:
                cb["maquinas"].append({"maquina": str(nome), "cv": _f(co.cell(row=r, column=2).value),
                                       "fator": _f(co.cell(row=r, column=3).value),
                                       "horas_dia": _f(co.cell(row=r, column=5).value)})

    iv = wb["Investimento"]
    pj["investimento"] = []
    for r in range(5, (_row(iv, "TOTAL") or 20)):
        nome = iv.cell(row=r, column=1).value
        if not nome:
            continue
        pj["investimento"].append({
            "item": str(nome), "unidade": iv.cell(row=r, column=3).value or "un",
            "quantidade": _f(iv.cell(row=r, column=4).value), "valor_unit": _f(iv.cell(row=r, column=5).value),
            "uso": _f(iv.cell(row=r, column=7).value, 1.0), "incluir": _f(iv.cell(row=r, column=8).value) >= 1,
            "vida": _f(iv.cell(row=r, column=9).value), "residual": _f(iv.cell(row=r, column=10).value)})

    if currais_csv is not None:
        df = pd.read_csv(currais_csv)
        pj["currais"] = []
        for _, row in df.iterrows():
            c = {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in row.items()}
            c["animais"] = c.pop("cab", 0) or 0
            c["mortes"] = c.pop("mortes_2026", 0) or 0
            pj["currais"].append(c)
    if vendas_csv is not None:
        pj["vendas"] = pd.read_csv(vendas_csv).to_dict(orient="records")
    elif "Dados_Reais" in wb.sheetnames:
        pj["vendas"] = _vendas_da_planilha(wb["Dados_Reais"])

    excel = {}
    try:
        cp = wb["Custo_Producao"]
        excel["coe"] = _f(cp.cell(row=_row(cp, "(=) COE"), column=3).value)
        excel["ct"] = _f(cp.cell(row=_row(cp, "(=) CT"), column=3).value)
        excel["receita"] = _f(wb["DRE"]["B5"].value)
        excel["res_op"] = _f(wb["DRE"]["B13"].value)
        excel["vpl"] = _f(wb["Fluxo_Caixa"]["B19"].value)
        excel["tir"] = _f(wb["Fluxo_Caixa"]["B20"].value, None)
    except Exception:
        pass
    return pj, excel


def achar_arquivo(nome: str, pastas=("dados", "dados/dados", ".", "dados/ilustracoes", "ilustracoes")) -> Path | None:
    """Procura o arquivo nas pastas mais prováveis (tolera upload em pasta errada no GitHub)."""
    raiz = Path(__file__).parent
    for p in pastas:
        cand = raiz / p / nome
        if cand.exists():
            return cand
    achados = list(raiz.rglob(nome))
    return achados[0] if achados else None


def exemplo_disponivel() -> bool:
    return achar_arquivo("exemplo_ilustrativo.json") is not None


def projeto_exemplo() -> dict:
    arq = achar_arquivo("exemplo_ilustrativo.json")
    if arq is None:            # sem o arquivo de exemplo, o sistema abre com um projeto em branco
        return projeto_em_branco()
    return de_json(arq.read_bytes())


def para_json(projeto: dict) -> bytes:
    return json.dumps(projeto, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def de_json(conteudo: bytes) -> dict:
    pj = json.loads(conteudo.decode("utf-8"))
    base = projeto_em_branco()
    for k, v in base.items():            # garante que todas as seções existem
        pj.setdefault(k, v)
    for k, v in base["premissas"].items():
        pj["premissas"].setdefault(k, v)
    for k, v in base["combustivel"].items():
        pj["combustivel"].setdefault(k, v)
    return pj
