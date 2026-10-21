"""Telas de projeto: Início e Cadastro passo a passo."""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
import streamlit as st

import ui
from engine import (BASES, GRUPOS, PREMISSAS_LOTE, PREMISSAS_MERCADO, REGIMES, REPOSICAO, SISTEMAS, _f,
                    capacidade_total, derivados, projeto_em_branco, resumo_combustivel, resumo_dieta,
                    resumo_investimento, validar, valor_anual_custos)
from projeto_io import de_json, exemplo_disponivel, para_json, projeto_de_excel, projeto_exemplo
from ui import brl, md, num, pct

PASSOS = ["Fazenda", "Currais", "Lote e desempenho", "Compra e venda", "Dieta", "Custos operacionais",
          "Combustível", "Investimento", "Vendas"]
DESCRICAO = {
    "Fazenda": "Quem é o projeto: fazenda, local, tipo de confinamento e regime tributário.",
    "Currais": "Cadastre os currais (linha, capacidade, área). A situação atual de cada curral é opcional.",
    "Lote e desempenho": "Quantos bois, por quanto tempo e com que desempenho esperado.",
    "Compra e venda": "Quanto custa o boi magro, quanto vale a arroba do gordo e a taxa de atratividade.",
    "Dieta": "Ingredientes em base de matéria seca (MS). A inclusão precisa somar 100%.",
    "Custos operacionais": "Equipe, sanidade, energia, manutenção e despesas comuns com o % rateado ao confinamento.",
    "Combustível": "Sem horímetro: estimamos o diesel pela rotina do trato e pela potência das máquinas.",
    "Investimento": "Instalações e máquinas a valor de reposição, com vida útil, residual e % de uso no confinamento.",
    "Vendas": "Opcional: lotes já vendidos, para comparar com o preço de equilíbrio.",
}


ILU_PASSO = {"Fazenda": "silo", "Currais": "cerca", "Lote e desempenho": "boi", "Compra e venda": "vaca",
             "Dieta": "milho", "Custos operacionais": "trator", "Combustível": "trator", "Investimento": "silo",
             "Vendas": "boi"}


def _slug(txt):
    return re.sub(r"[^a-z0-9]+", "_", (txt or "projeto").lower()).strip("_") or "projeto"


def status_passos(pj, pend) -> dict:
    tem = {
        "Fazenda": bool(pj["fazenda"].get("nome")), "Currais": bool(pj["currais"]),
        "Lote e desempenho": True, "Compra e venda": True, "Dieta": bool(pj["dieta"]),
        "Custos operacionais": any(_f(c.get("valor_unit")) > 0 for c in pj["custos"]),
        "Combustível": resumo_combustivel(pj)["custo_ano"] > 0,
        "Investimento": bool(pj["investimento"]), "Vendas": bool(pj["vendas"]),
    }
    return {k: ("ok" if tem[k] and not pend[k] else ("opcional" if k == "Vendas" and not pj["vendas"] else "pendente"))
            for k in PASSOS}


def tags_status(st_passos):
    html = ""
    for i, k in enumerate(PASSOS):
        s = st_passos[k]
        cls = "" if s == "ok" else ("off" if s == "opcional" else "warn")
        marca = "✓" if s == "ok" else ("·" if s == "opcional" else "!")
        html += f'<span class="tag {cls}">{marca} {i + 1}. {k}</span>'
    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# INÍCIO
# ============================================================================
def pagina_inicio():
    st.session_state.last_page = "inicio"
    c = ui.contexto()
    pj = c.pj
    f = pj["fazenda"]
    local = ", ".join(x for x in (f.get("municipio"), f.get("uf")) if x)
    chips = [local, f.get("sistema", ""), f.get("ciclo") or "", f"{num(len(pj['currais']))} currais",
             f"{num(capacidade_total(pj))} vagas"]
    st.markdown(
        f'<div class="oc-boas"><div class="k">ConfinaCusto · custos de confinamento</div>'
        f'<h2>{ui.nome_fazenda(pj)}</h2>'
        f'<p>Cadastre o confinamento, acompanhe os custos em tempo real e emita os relatórios de viabilidade — '
        f'COE, COT, CT, DRE, VPL, TIR e payback.</p>'
        f'<div class="chips">{"".join(f"<span>{x}</span>" for x in chips if x)}</div>'
        f'{ui.ilu("trator", "t")}{ui.ilu("vaca", "v")}{ui.ilu("milho", "m")}</div>', unsafe_allow_html=True)
    st.write("")

    h = st.columns(3)
    if c.ok:
        r = c.r
        h[0].markdown(ui.hero("Resultado por boi", brl(r["res_op_cab"]), f"{ui.mi(r['res_op'])} no ano", "boi", "ouro"),
                      unsafe_allow_html=True)
        h[1].markdown(ui.hero("Custo da @ produzida", brl(r["cprod_coe"], 2), "custo operacional, sem o boi magro",
                              "milho", "escuro"), unsafe_allow_html=True)
        h[2].markdown(ui.hero("Diária operacional", f"{brl(r['diaria_op'], 2)}",
                              f"R$/cab/dia · média de Goiás {brl(ui.BENCH['Goiás'], 2)}", "trator", "teal"),
                      unsafe_allow_html=True)
    else:
        h[0].markdown(ui.hero("Resultado por boi", "—", "complete o cadastro para calcular", "boi", "ouro"),
                      unsafe_allow_html=True)
        h[1].markdown(ui.hero("Bois por ciclo", num(_f(pj["premissas"].get("cab"))), "lote e desempenho", "milho"),
                      unsafe_allow_html=True)
        h[2].markdown(ui.hero("Capacidade", f"{num(capacidade_total(pj))} vagas", f"{len(pj['currais'])} currais",
                              "cerca", "teal"), unsafe_allow_html=True)
    st.write("")

    e, d = st.columns([1.6, 1], gap="medium")
    with e, ui.card():
        ui.titulo_card("Andamento do cadastro", "clique em Editar cadastro para continuar de onde parou")
        tags_status(status_passos(pj, c.pend))
        b = st.columns(3)
        b[0].page_link(ui.PAGINAS["cadastro"], label="Editar cadastro", icon=":material/edit_note:")
        b[1].page_link(ui.PAGINAS["painel"], label="Ver painel", icon=":material/dashboard:")
        b[2].page_link(ui.PAGINAS["relatorios"], label="Emitir relatórios", icon=":material/description:")
    with d, ui.card():
        ui.titulo_card("Salvar ou trocar de projeto", "o sistema não guarda nada sozinho na nuvem")
        st.download_button("Baixar projeto (.json)", para_json(pj), file_name=f"{_slug(f.get('nome'))}.json",
                           mime="application/json", icon=":material/download:", width="stretch")
        if st.button("Trocar de projeto", icon=":material/swap_horiz:", width="stretch", key="trocar"):
            st.session_state.escolheu = False
            st.rerun()
        st.caption("Baixe o arquivo antes de trocar: o que não foi salvo se perde.")

    st.write("")
    st.markdown('<div class="oc-kicker">Como funciona</div>', unsafe_allow_html=True)
    st.write("")
    x = st.columns(3)
    for col, (n, t, desc, img) in zip(x, [
        ("1", "Cadastrar", "Fazenda, currais, lote, mercado, dieta, custos, combustível e investimento — "
                          "com o resultado mudando ao vivo enquanto você digita.", "cerca"),
        ("2", "Acompanhar", "Painel de indicadores, mapa dos currais e simulador de cenários com análise de risco "
                           "(Monte Carlo).", "boi"),
        ("3", "Emitir relatórios", "Custo de produção (COE, COT, CT), DRE, fluxo de caixa e viabilidade em Excel "
                                  "ou prontos para imprimir.", "milho"),
    ]):
        with col, ui.card(hover=True):
            st.markdown(f'<div class="oc-passo"><div><div class="passo-titulo">Passo {n}</div>'
                        f'<div class="oc-card-tit">{t}</div><div class="oc-card-sub">{desc}</div></div>'
                        f'{ui.ilu(img)}</div>', unsafe_allow_html=True)


# ============================================================================
# TELA DE ENTRADA (primeira decisão do usuário)
# ============================================================================
def _entrar(pj, pagina, passo=0):
    ui.carregar_projeto(pj, passo=passo)
    st.session_state.escolheu = True
    st.switch_page(ui.PAGINAS[pagina])


def tela_entrada():
    with st.container(key="gate"):
        st.markdown(
            f'<div class="gate-marca">{ui.ilu("vaca")}<div>Confina<span>Custo</span></div></div>'
            '<div class="oc-kicker gate-k">Custos e viabilidade de confinamento</div>'
            '<div class="gate-h1">Como você quer começar?</div>'
            '<div class="gate-sub">Veja o sistema funcionando com um exemplo pronto, ou cadastre o seu '
            'confinamento do zero.</div>', unsafe_allow_html=True)
        e, d = st.columns(2, gap="medium")
        with e, st.container(key="gate-ouro"):
            st.markdown(
                '<div class="gate-txt"><span class="gate-tag">EXEMPLO PRONTO</span>'
                '<div class="gate-h2">Ver um exemplo pronto</div>'
                '<p>Um confinamento fictício em Goiás, com números ilustrativos.</p>'
                '<ul class="gate-lista"><li>1.850 bois em 15 currais</li><li>R$ 1.080 de resultado por boi</li>'
                '<li>Painel, mapa, simulador e relatórios prontos</li></ul></div>'
                f'<div class="gate-ilu">{ui.ilu("boi", "a")}{ui.ilu("milho", "b")}</div>', unsafe_allow_html=True)
            if st.button("Abrir o exemplo →", key="g_exemplo"):
                _entrar(projeto_exemplo(), "painel")
        with d, st.container(key="gate-verde"):
            st.markdown(
                '<div class="gate-txt"><span class="gate-tag">MEU CONFINAMENTO</span>'
                '<div class="gate-h2">Começar um projeto novo</div>'
                '<p>O cadastro guia você em 9 passos, com o resultado mudando enquanto digita.</p>'
                '<ul class="gate-lista"><li>Fazenda, currais, lote e dieta</li><li>Custos, diesel e investimento</li>'
                '<li>Salve e continue depois (.json)</li></ul></div>'
                f'<div class="gate-ilu">{ui.ilu("cerca", "a")}{ui.ilu("vaca", "b")}</div>', unsafe_allow_html=True)
            if st.button("Criar projeto novo →", key="g_novo"):
                _entrar(projeto_em_branco(), "cadastro")
        with st.container(key="gate-links"):
            with st.popover("Abrir projeto salvo (.json)", icon=":material/upload_file:"):
                arq = st.file_uploader("Arquivo .json", type=["json"], key="up_json")
                if arq is not None and st.button("Abrir", key="btn_json", type="primary", width="stretch"):
                    try:
                        novo = de_json(arq.getvalue())
                    except Exception as ex:
                        st.error(f"Não consegui ler o arquivo: {ex}")
                    else:
                        _entrar(novo, "inicio")
            with st.popover("Importar planilha (.xlsx)", icon=":material/table_view:"):
                arq2 = st.file_uploader("Planilha .xlsx no formato da ferramenta", type=["xlsx"], key="up_xlsx")
                if arq2 is not None and st.button("Importar", key="btn_xlsx", type="primary", width="stretch"):
                    try:
                        novo, _ = projeto_de_excel(io.BytesIO(arq2.getvalue()))
                        novo["fazenda"]["nome"] = arq2.name.rsplit(".", 1)[0]
                    except Exception as ex:
                        st.error(f"A planilha não está no formato da ferramenta: {ex}")
                    else:
                        _entrar(novo, "cadastro", passo=1)
        st.markdown('<div class="gate-nota">Custos nos Agronegócios · UnB · Marcos da Silva Oliveira e Ana Beatriz Liberal Dionizio</div>', unsafe_allow_html=True)


# ============================================================================
# CADASTRO
# ============================================================================
def _snap(nome, df_fn):
    """Fotografia estável dos dados de um editor enquanto o usuário está no passo."""
    snaps = st.session_state.setdefault("snaps", {})
    if nome not in snaps:
        snaps[nome] = df_fn()
    return snaps[nome]


def _reset_snaps():
    st.session_state["snaps"] = {}
    st.session_state["snap_gen"] = st.session_state.get("snap_gen", 0) + 1


def _key(nome):
    return f"{nome}_{st.session_state.get('ver', 0)}_{st.session_state.get('snap_gen', 0)}"


def _campo(pj, sec, k, rotulo, unid, tipo, ajuda, col):
    cur = _f(pj[sec].get(k))
    key = _key(f"in_{sec}_{k}")
    if tipo == "pct":
        v = col.number_input(f"{rotulo} ({unid})", value=round(cur * 100, 4), step=0.1, format="%.2f", key=key,
                             help=ajuda)
        pj[sec][k] = v / 100
    elif tipo == "int":
        v = col.number_input(f"{rotulo} ({unid})", value=int(round(cur)), step=1, min_value=0, key=key, help=ajuda)
        pj[sec][k] = int(v)
    else:
        v = col.number_input(f"{rotulo} ({unid})", value=float(cur), step=0.01, format="%.2f", min_value=0.0,
                             key=key, help=ajuda)
        pj[sec][k] = float(v)


def _df_records(df, colunas):
    out = []
    for _, row in df.iterrows():
        rec = {}
        for c in colunas:
            v = row.get(c)
            if isinstance(v, (np.generic,)):
                v = v.item()
            if v is not None and isinstance(v, float) and np.isnan(v):
                v = None
            rec[c] = v
        out.append(rec)
    return out


def passo_fazenda(pj):
    f = pj["fazenda"]
    a, b = st.columns(2)
    f["nome"] = a.text_input("Nome da fazenda / projeto", f.get("nome", ""), key=_key("f_nome"))
    f["responsavel"] = b.text_input("Responsável", f.get("responsavel", ""), key=_key("f_resp"))
    a, b, c = st.columns([2, 1, 2])
    f["municipio"] = a.text_input("Município", f.get("municipio", ""), key=_key("f_mun"))
    f["uf"] = b.text_input("UF", f.get("uf", ""), max_chars=2, key=_key("f_uf"))
    f["ciclo"] = c.text_input("Ciclo / safra", f.get("ciclo", ""), placeholder="ex.: Giro 2026", key=_key("f_ciclo"))
    a, b, c = st.columns(3)
    f["sistema"] = a.selectbox("Tipo de confinamento", SISTEMAS,
                               index=SISTEMAS.index(f.get("sistema")) if f.get("sistema") in SISTEMAS else 0,
                               key=_key("f_sis"))
    f["reposicao"] = b.selectbox("Origem dos animais", REPOSICAO,
                                 index=REPOSICAO.index(f.get("reposicao")) if f.get("reposicao") in REPOSICAO else 0,
                                 key=_key("f_rep"))
    reg = c.selectbox("Regime tributário", REGIMES,
                      index=REGIMES.index(f.get("regime")) if f.get("regime") in REGIMES else 0, key=_key("f_reg"))
    if reg != f.get("regime"):
        f["regime"] = reg
        if reg == REGIMES[0]:
            pj["premissas"]["funrural"] = 0.015
    if f.get("reposicao") != REPOSICAO[0]:
        st.info("Reposição própria: no passo **Compra e venda**, use o valor de mercado do boi magro "
                "(custo de oportunidade — valor de reposição, Módulo 5).")
    if f.get("regime") == REGIMES[1]:
        st.info("Pessoa jurídica: ajuste a contribuição sobre a venda e inclua os encargos patronais na folha.")


COLS_CURRAL = {"curral": "Curral", "linha": "Linha", "capacidade": "Capacidade (cab)", "area_ha": "Área (ha)",
               "animais": "Animais hoje", "sexo": "Categoria", "dias_cocho": "Dias de cocho", "gmd": "GMD (kg)",
               "peso_entrada": "Peso entrada (kg)", "peso_proj": "Peso projetado (kg)",
               "custo_cab": "Custo acumulado/boi (R$)", "mortes": "Mortes"}


def passo_currais(pj):
    with st.expander("Gerar currais automaticamente", expanded=not pj["currais"]):
        g = st.columns(4)
        n = g[0].number_input("Nº de currais", 1, 200, 12, key=_key("g_n"))
        lin = g[1].number_input("Nº de linhas de cocho", 1, 10, 2, key=_key("g_l"))
        cap = g[2].number_input("Capacidade por curral (cab)", 1, 2000, 150, key=_key("g_c"))
        area = g[3].number_input("Área por curral (ha)", 0.0, 10.0, 0.25, key=_key("g_a"))
        if st.button("Gerar e substituir a lista", icon=":material/auto_awesome:"):
            por_linha = int(np.ceil(n / lin))
            pj["currais"] = [{"curral": i + 1, "linha": i // por_linha + 1, "capacidade": cap, "area_ha": area,
                              "animais": 0, "sexo": "M"} for i in range(int(n))]
            pj["premissas"]["cap"] = capacidade_total(pj)
            _reset_snaps()
            st.rerun()

    df = _snap("currais", lambda: pd.DataFrame(
        [{k: c.get(k) for k in COLS_CURRAL} for c in pj["currais"]], columns=list(COLS_CURRAL)))
    ed = st.data_editor(
        df, key=_key("ed_currais"), num_rows="dynamic", hide_index=True,
        column_config={
            "curral": st.column_config.NumberColumn("Curral", min_value=1, step=1, required=True),
            "linha": st.column_config.NumberColumn("Linha", min_value=1, step=1, required=True, default=1),
            "capacidade": st.column_config.NumberColumn("Capacidade (cab)", min_value=0, step=1, default=0),
            "area_ha": st.column_config.NumberColumn("Área (ha)", min_value=0.0, format="%.2f"),
            "animais": st.column_config.NumberColumn("Animais hoje", min_value=0, step=1, default=0),
            "sexo": st.column_config.SelectboxColumn("Categoria", options=["M", "F"], default="M",
                                                     help="M = machos (bois), F = fêmeas"),
            "dias_cocho": st.column_config.NumberColumn("Dias de cocho", min_value=0.0, format="%.0f"),
            "gmd": st.column_config.NumberColumn("GMD (kg)", min_value=0.0, format="%.2f"),
            "peso_entrada": st.column_config.NumberColumn("Peso entrada (kg)", min_value=0.0, format="%.0f"),
            "peso_proj": st.column_config.NumberColumn("Peso projetado (kg)", min_value=0.0, format="%.0f"),
            "custo_cab": st.column_config.NumberColumn("Custo acumulado/boi", min_value=0.0, format="R$ %.0f"),
            "mortes": st.column_config.NumberColumn("Mortes", min_value=0, step=1),
        },
    )
    antigos = {c.get("curral"): c for c in pj["currais"]}
    novos = []
    for rec in _df_records(ed, list(COLS_CURRAL)):
        if rec.get("curral") is None:
            continue
        base = dict(antigos.get(rec["curral"], {}))     # preserva dados extras (ex.: composição do custo)
        base.update({k: v for k, v in rec.items()})
        novos.append(base)
    pj["currais"] = novos
    pj["premissas"]["cap"] = capacidade_total(pj)
    st.caption("Colunas a partir de 'Animais hoje' são a situação atual de cada curral (opcional) — alimentam o "
               "mapa e a margem projetada por curral.")
    k = st.columns(3)
    k[0].metric("Currais", num(len(novos)))
    k[1].metric("Linhas de cocho", num(len({c.get('linha') for c in novos})))
    k[2].metric("Capacidade estática", f"{num(capacidade_total(pj))} vagas")


def passo_lote(pj):
    cols = st.columns(2)
    for i, (k, rot, un, tp, aj) in enumerate(PREMISSAS_LOTE):
        _campo(pj, "premissas", k, rot, un, tp, aj, cols[i % 2])
    p = {k: _f(v) for k, v in pj["premissas"].items()}
    d = derivados(p)
    st.markdown('<div class="passo-titulo">Calculado automaticamente</div>', unsafe_allow_html=True)
    k = st.columns(4)
    k[0].metric("Peso de saída", f"{num(d['ps'], 0)} kg")
    k[1].metric("@ de carcaça por boi", num(d["arr_sai"], 2))
    k[2].metric("@ produzidas por boi", num(d["arr_prod"], 2))
    cap = capacidade_total(pj)
    k[3].metric("Ocupação (bois ÷ vagas)", pct(p["cab"] / cap, 0) if cap else "cadastre os currais")


def passo_mercado(pj):
    cols = st.columns(2)
    for i, (k, rot, un, tp, aj) in enumerate(PREMISSAS_MERCADO):
        _campo(pj, "premissas", k, rot, un, tp, aj, cols[i % 2])
    p = {k: _f(v) for k, v in pj["premissas"].items()}
    d = derivados(p)
    if p["vcompra"] > 0 and p["pvenda"] > 0:
        st.markdown('<div class="passo-titulo">Referências</div>', unsafe_allow_html=True)
        k = st.columns(3)
        k[0].metric("Boi magro em R$/@ (sobre o peso de entrada)", brl(p["vcompra"] / (p["pe"] / 30), 2) if p["pe"] else "—")
        k[1].metric("Valor do boi gordo", brl(d["arr_sai"] * p["pvenda"]))
        k[2].metric("Relação de troca (gordo ÷ magro)", num(d["arr_sai"] * p["pvenda"] / p["vcompra"], 2))


def passo_dieta(pj):
    df = _snap("dieta", lambda: pd.DataFrame(
        [{"ingrediente": i.get("ingrediente"), "ms": _f(i.get("ms")) * 100, "inclusao": _f(i.get("inclusao")) * 100,
          "preco_t": _f(i.get("preco_t"))} for i in pj["dieta"]],
        columns=["ingrediente", "ms", "inclusao", "preco_t"]))
    ed = st.data_editor(
        df, key=_key("ed_dieta"), num_rows="dynamic", hide_index=True,
        column_config={
            "ingrediente": st.column_config.TextColumn("Ingrediente", required=True),
            "ms": st.column_config.NumberColumn("MS do alimento (%)", min_value=0.0, max_value=100.0, format="%.1f"),
            "inclusao": st.column_config.NumberColumn("Inclusão (% da MS da dieta)", min_value=0.0, max_value=100.0,
                                                      format="%.2f"),
            "preco_t": st.column_config.NumberColumn("Preço (R$/t matéria natural)", min_value=0.0, format="R$ %.2f"),
        },
    )
    pj["dieta"] = [{"ingrediente": r["ingrediente"], "ms": _f(r["ms"]) / 100, "inclusao": _f(r["inclusao"]) / 100,
                    "preco_t": _f(r["preco_t"])} for r in _df_records(ed, ["ingrediente", "ms", "inclusao", "preco_t"])
                   if r.get("ingrediente")]
    rd = resumo_dieta(pj["dieta"])
    p = {k: _f(v) for k, v in pj["premissas"].items()}
    d = derivados(p)
    k = st.columns(4)
    ok = abs(rd["inclusao_total"] - 1) <= 0.005
    k[0].metric("Soma da inclusão", pct(rd["inclusao_total"]), delta="ok" if ok else "precisa ser 100%",
                delta_color="normal" if ok else "inverse")
    k[1].metric("Custo da dieta", f"{brl(rd['custo_kg_ms'], 3)}/kg MS")
    k[2].metric("Consumo de MS", f"{num(d['cms_kg'], 2)} kg/cab/dia")
    k[3].metric("Custo alimentar", f"{brl(rd['custo_kg_ms'] * d['cms_kg'], 2)}/cab/dia")
    st.caption("Dica: a % de MS de cada alimento vem da análise bromatológica ou da tabela do nutricionista.")


BASE_ROTULO = {v: k for k, v in BASES.items()}


def passo_custos(pj):
    def montar():
        linhas = []
        for c in pj["custos"]:
            em_pct = c.get("base") in ("pct_bens", "pct_folha")
            linhas.append({"item": c.get("item"), "grupo": c.get("grupo") or "Outros",
                           "classe": c.get("classe") or "Fixo", "base": BASES.get(c.get("base", "fixo")),
                           "quantidade": _f(c.get("quantidade"), 1.0),
                           "valor_unit": _f(c.get("valor_unit")) * (100 if em_pct else 1),
                           "multiplicador": _f(c.get("multiplicador"), 1.0), "rateio": _f(c.get("rateio"), 1.0) * 100})
        return pd.DataFrame(linhas, columns=["item", "grupo", "classe", "base", "quantidade", "valor_unit",
                                             "multiplicador", "rateio"])

    ed = st.data_editor(
        _snap("custos", montar), key=_key("ed_custos"), num_rows="dynamic", hide_index=True,
        column_config={
            "item": st.column_config.TextColumn("Item", required=True, width="medium"),
            "grupo": st.column_config.SelectboxColumn("Grupo", options=GRUPOS, default="Outros"),
            "classe": st.column_config.SelectboxColumn("Classe", options=["Fixo", "Variável"], default="Fixo"),
            "base": st.column_config.SelectboxColumn("Base de cálculo", options=list(BASES.values()),
                                                     default=BASES["fixo"]),
            "quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, format="%.2f", default=1.0),
            "valor_unit": st.column_config.NumberColumn("Valor unitário (R$ ou %)", min_value=0.0, format="%.2f",
                                                        help="Para as bases em %, digite o percentual (3 = 3%)."),
            "multiplicador": st.column_config.NumberColumn("Multiplicador", min_value=0.0, format="%.2f", default=1.0,
                                                           help="Ex.: 12 para valor mensal; 13,33 para salário com "
                                                                "13º e 1/3 de férias."),
            "rateio": st.column_config.NumberColumn("% rateio", min_value=0.0, max_value=100.0, format="%.1f",
                                                    default=100.0, help="Parte da despesa que cabe ao confinamento."),
        },
    )
    novos = []
    for r in _df_records(ed, ["item", "grupo", "classe", "base", "quantidade", "valor_unit", "multiplicador", "rateio"]):
        if not r.get("item"):
            continue
        base = BASE_ROTULO.get(r.get("base"), "fixo")
        em_pct = base in ("pct_bens", "pct_folha")
        novos.append({"item": r["item"], "grupo": r.get("grupo") or "Outros", "classe": r.get("classe") or "Fixo",
                      "base": base, "quantidade": _f(r.get("quantidade"), 1.0),
                      "valor_unit": _f(r.get("valor_unit")) / (100 if em_pct else 1),
                      "multiplicador": _f(r.get("multiplicador"), 1.0), "rateio": _f(r.get("rateio"), 100) / 100})
    pj["custos"] = novos

    linhas = valor_anual_custos(pj)
    tab = pd.DataFrame([{"Item": l["item"], "Custo no ano": l["anual"]} for l in linhas])
    e, d = st.columns([1.6, 1])
    with e:
        st.markdown('<div class="passo-titulo">Custo anual calculado</div>', unsafe_allow_html=True)
        st.dataframe(tab, hide_index=True, column_config={
            "Custo no ano": st.column_config.NumberColumn(format="R$ %.0f")})
    with d:
        tot = sum(l["anual"] or 0 for l in linhas)
        fixos = sum(l["anual"] or 0 for l in linhas if l["classe"] == "Fixo")
        st.metric("Total no ano", brl(tot), border=True)
        st.metric("dos quais fixos", brl(fixos), border=True)
        with st.expander("Calcular um % de rateio (cabeças-dia)"):
            p = {k: _f(v) for k, v in pj["premissas"].items()}
            cd = derivados(p)["cab_dia"]
            reb = st.number_input("Rebanho médio a pasto (fora do confinamento)", 0, 100000, 462, key=_key("reb"))
            sug = cd / (cd + reb * 365) if cd else 0
            md(f"Cabeças-dia do confinamento: **{num(cd)}**  \nRateio sugerido: **{pct(sug)}**")
            st.caption("Use esse % nas despesas comuns da fazenda que não têm medição própria (Módulo 9).")
    st.caption("Diesel e gasolina entram no passo seguinte. Bases: valor no ano · por boi que entra · por "
               "cabeça-dia · % do valor dos bens (manutenção) · % sobre a folha (encargos).")


def passo_combustivel(pj):
    cb = pj["combustivel"]
    a, b, c, d = st.columns(4)
    for col, k, rot, fmt, passo in ((a, "preco_diesel", "Preço do diesel (R$/L)", "%.2f", 0.01),
                                    (b, "coef", "Coeficiente L/h por kW", "%.3f", 0.001),
                                    (c, "carga_batida", "Carga por batida do misturador (t)", "%.1f", 0.5),
                                    (d, "min_carga", "Min por batida — carregamento", "%.0f", 1.0)):
        cb[k] = col.number_input(rot, value=float(_f(cb.get(k))), step=passo, format=fmt, min_value=0.0,
                                 key=_key(f"cb_{k}"))
    a, b, c, d = st.columns(4)
    cb["min_mistura"] = a.number_input("Min por batida — mistura", value=float(_f(cb.get("min_mistura"))),
                                       step=1.0, format="%.0f", min_value=0.0, key=_key("cb_mm"))
    cb["min_distrib"] = b.number_input("Min por batida — distribuição", value=float(_f(cb.get("min_distrib"))),
                                       step=1.0, format="%.0f", min_value=0.0, key=_key("cb_md"))
    rc = resumo_combustivel(pj)
    c.metric("Ração fornecida por dia", f"{num(rc['mn_dia'], 1)} t")
    d.metric("Batidas por dia", num(rc["batidas"]))
    hs = rc["horas_sugeridas"]
    st.caption(f"Horas sugeridas pela rotina: misturador {num(hs['misturador'], 1)} h/dia · distribuidor "
               f"{num(hs['distribuidor'], 1)} h/dia · pá carregadeira {num(hs['pa'], 1)} h/dia (+ silo e limpeza).")

    df = _snap("maquinas", lambda: pd.DataFrame(cb.get("maquinas", []), columns=["maquina", "cv", "fator", "horas_dia"]))
    ed = st.data_editor(df, key=_key("ed_maq"), num_rows="dynamic", hide_index=True, column_config={
        "maquina": st.column_config.TextColumn("Máquina / operação", required=True, width="medium"),
        "cv": st.column_config.NumberColumn("Potência (cv)", min_value=0.0, format="%.0f", default=100.0),
        "fator": st.column_config.NumberColumn("Fator de uso", min_value=0.0, max_value=2.0, format="%.2f",
                                               default=1.0, help="1 = esforço médio; menor para trabalho leve."),
        "horas_dia": st.column_config.NumberColumn("Horas por dia", min_value=0.0, format="%.2f", default=0.0),
    })
    cb["maquinas"] = [r for r in _df_records(ed, ["maquina", "cv", "fator", "horas_dia"]) if r.get("maquina")]

    a, b, c = st.columns(3)
    cb["km_dia"] = a.number_input("Veículo de apoio — km por dia", value=float(_f(cb.get("km_dia"))), step=5.0,
                                  min_value=0.0, key=_key("cb_km"))
    cb["km_l"] = b.number_input("Consumo (km/L)", value=float(_f(cb.get("km_l"), 10)), step=0.5, min_value=0.0,
                                key=_key("cb_kml"))
    cb["preco_gasolina"] = c.number_input("Preço da gasolina (R$/L)", value=float(_f(cb.get("preco_gasolina"))),
                                          step=0.01, min_value=0.0, key=_key("cb_pg"))
    rc = resumo_combustivel(pj)
    p = {k: _f(v) for k, v in pj["premissas"].items()}
    cab_ent = derivados(p)["cab_ent"]
    k = st.columns(4)
    k[0].metric("Diesel no ano", f"{num(rc['litros_diesel'])} L", border=True)
    k[1].metric("Gasolina no ano", f"{num(rc['litros_gasolina'])} L", border=True)
    k[2].metric("Custo no ano", brl(rc["custo_ano"]), border=True)
    k[3].metric("Por boi", brl(rc["custo_ano"] / cab_ent if cab_ent else 0), border=True)
    st.caption("Regra prática (Revista Cultivar): L/h ≈ potência em kW × 0,243, para um trator a ~55% da carga.")


def passo_investimento(pj):
    df = _snap("invest", lambda: pd.DataFrame(
        [{"item": i.get("item"), "unidade": i.get("unidade"), "quantidade": _f(i.get("quantidade")),
          "valor_unit": _f(i.get("valor_unit")), "uso": _f(i.get("uso"), 1) * 100, "incluir": bool(i.get("incluir", True)),
          "vida": _f(i.get("vida")), "residual": _f(i.get("residual")) * 100} for i in pj["investimento"]],
        columns=["item", "unidade", "quantidade", "valor_unit", "uso", "incluir", "vida", "residual"]))
    ed = st.data_editor(df, key=_key("ed_inv"), num_rows="dynamic", hide_index=True, column_config={
        "item": st.column_config.TextColumn("Item", required=True, width="medium"),
        "unidade": st.column_config.TextColumn("Unid.", default="un"),
        "quantidade": st.column_config.NumberColumn("Qtd", min_value=0.0, format="%.0f", default=1.0),
        "valor_unit": st.column_config.NumberColumn("Valor unit. (R$)", min_value=0.0, format="R$ %.0f"),
        "uso": st.column_config.NumberColumn("% uso no confin.", min_value=0.0, max_value=100.0, format="%.0f",
                                             default=100.0),
        "incluir": st.column_config.CheckboxColumn("Investir no ano 0", default=True,
                                                   help="Desmarque para bens que já existem e não serão comprados."),
        "vida": st.column_config.NumberColumn("Vida útil (anos)", min_value=0.0, format="%.0f", default=10.0),
        "residual": st.column_config.NumberColumn("Residual (%)", min_value=0.0, max_value=100.0, format="%.0f",
                                                  default=0.0),
    })
    pj["investimento"] = [{"item": r["item"], "unidade": r.get("unidade") or "un", "quantidade": _f(r.get("quantidade")),
                           "valor_unit": _f(r.get("valor_unit")), "uso": _f(r.get("uso"), 100) / 100,
                           "incluir": bool(r.get("incluir", True)), "vida": _f(r.get("vida")),
                           "residual": _f(r.get("residual")) / 100}
                          for r in _df_records(ed, ["item", "unidade", "quantidade", "valor_unit", "uso", "incluir",
                                                    "vida", "residual"]) if r.get("item")]
    ri = resumo_investimento(pj["investimento"])
    cap = capacidade_total(pj)
    k = st.columns(4)
    k[0].metric("Valor atribuído ao confinamento", brl(ri["valor_bens"]), border=True)
    k[1].metric("Investimento no ano 0", brl(ri["desembolso"]), border=True)
    k[2].metric("Depreciação por ano", brl(ri["depreciacao"]), border=True)
    k[3].metric("Por vaga", brl(ri["valor_bens"] / cap) if cap else "—", border=True)


def passo_vendas(pj):
    if not pj["vendas"] and exemplo_disponivel():
        if st.button("Trazer as vendas do exemplo (11 lotes ilustrativos)", icon=":material/download:"):
            pj["vendas"] = projeto_exemplo()["vendas"]
            _reset_snaps()
            st.rerun()
    st.caption("Clique na última linha da tabela para adicionar um lote. A linha só entra no cálculo depois que a "
               "**data** estiver preenchida.")
    df = _snap("vendas", lambda: pd.DataFrame(
        [{"data": pd.to_datetime(v.get("data")).date() if v.get("data") else None, "comprador": v.get("comprador"),
          "animais": _f(v.get("animais")), "peso_carcaca": _f(v.get("peso_carcaca")),
          "rendimento": _f(v.get("rendimento")) * 100, "preco_arroba": _f(v.get("preco_arroba"))} for v in pj["vendas"]],
        columns=["data", "comprador", "animais", "peso_carcaca", "rendimento", "preco_arroba"]).astype(
        {"comprador": "string", "animais": "float64", "peso_carcaca": "float64", "rendimento": "float64",
         "preco_arroba": "float64"}))
    ed = st.data_editor(df, key=_key("ed_vendas"), num_rows="dynamic", hide_index=True, column_config={
        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
        "comprador": st.column_config.TextColumn("Comprador / frigorífico"),
        "animais": st.column_config.NumberColumn("Animais", min_value=0, step=1),
        "peso_carcaca": st.column_config.NumberColumn("Peso de carcaça (kg/cab)", min_value=0.0, format="%.1f"),
        "rendimento": st.column_config.NumberColumn("Rendimento (%)", min_value=0.0, max_value=100.0, format="%.2f"),
        "preco_arroba": st.column_config.NumberColumn("Preço (R$/@)", min_value=0.0, format="R$ %.2f"),
    })
    vendas = []
    for r in _df_records(ed, ["data", "comprador", "animais", "peso_carcaca", "rendimento", "preco_arroba"]):
        if not r.get("data"):
            continue
        n, pc, pr = _f(r.get("animais")), _f(r.get("peso_carcaca")), _f(r.get("preco_arroba"))
        vendas.append({"data": str(pd.to_datetime(r["data"]).date()), "comprador": r.get("comprador") or "",
                       "animais": n, "peso_carcaca": pc, "rendimento": _f(r.get("rendimento")) / 100,
                       "preco_arroba": pr, "valor_total": n * pc / 15 * pr})
    pj["vendas"] = vendas
    if vendas:
        tot = sum(v["valor_total"] for v in vendas)
        arr = sum(v["animais"] * v["peso_carcaca"] / 15 for v in vendas)
        k = st.columns(3)
        k[0].metric("Animais vendidos", num(sum(v["animais"] for v in vendas)), border=True)
        k[1].metric("Receita das vendas", brl(tot), border=True)
        k[2].metric("Preço médio", f"{brl(tot / arr, 2) if arr else '—'}/@", border=True)


FUNCOES = [passo_fazenda, passo_currais, passo_lote, passo_mercado, passo_dieta, passo_custos, passo_combustivel,
           passo_investimento, passo_vendas]


def _ir_para(i):
    st.session_state.passo = i
    st.session_state.seg_gen = st.session_state.get("seg_gen", 0) + 1
    _reset_snaps()


def painel_vivo(c):
    with ui.card():
        st.markdown('<span class="vivo">● RESULTADO EM TEMPO REAL</span>', unsafe_allow_html=True)
        if not c.ok:
            st.caption("Complete os passos marcados com ! para ver os resultados.")
            for k, v in c.pend.items():
                if v and k != "Investimento":
                    md(f"**{k}:** " + " ".join(v))
            return
        r = c.r
        st.metric("Resultado operacional por boi", brl(r["res_op_cab"]))
        st.metric("Resultado no ano", ui.mi(r["res_op"]))
        st.metric("Custo da @ produzida (COE)", f"{brl(r['cprod_coe'], 2)}")
        st.metric("Preço de equilíbrio (custo total)", f"{brl(r['pe_ct'], 2)}/@",
                  delta=f"venda {brl(r['p']['pvenda'], 2)}", delta_color="off")
        st.metric("Diária operacional", f"{brl(r['diaria_op'], 2)}/cab/dia",
                  delta=f"{num(r['diaria_op'] - ui.BENCH['Goiás'], 2)} vs. média GO", delta_color="inverse")
        st.metric("VPL (10 anos)", ui.mi(r["vpl"]) if r.get("vpl") is not None else "—")
        if c.pend.get("Investimento"):
            st.caption("Sem investimento cadastrado: VPL e payback ficam incompletos.")


def vivo_mobile(c):
    """Faixa fixa com o resultado ao vivo (só aparece no celular, onde o painel da direita fica lá embaixo)."""
    with st.container(key="vivomob"):
        if c.ok:
            r = c.r
            html = (f'<div class="oc-vivomob"><div><span>RESULTADO/BOI</span><b class="ouro">{brl(r["res_op_cab"])}</b></div>'
                    f'<div><span>EQUILÍBRIO</span><b>{brl(r["pe_ct"], 2)}</b></div>'
                    f'<div><span>DIÁRIA</span><b>{brl(r["diaria_op"], 2)}</b></div></div>')
        else:
            html = ('<div class="oc-vivomob"><div><span>RESULTADO AO VIVO</span><b>complete os passos com !</b></div></div>')
        st.markdown(html, unsafe_allow_html=True)


def pagina_cadastro():
    entrou_agora = st.session_state.get("last_page") != "cadastro"
    st.session_state.last_page = "cadastro"
    if entrou_agora:
        _reset_snaps()
    pj = st.session_state.projeto
    ui.topo("Projeto", "Cadastro do projeto",
            f"{ui.nome_fazenda(pj)} · preencha na ordem; tudo que você digita entra no cálculo na hora.")

    vivo_mobile(ui.contexto())
    passo = st.session_state.get("passo", 0)
    stp = status_passos(pj, validar(pj))
    marca = {"ok": "✓", "pendente": "!", "opcional": "·"}
    sel = st.segmented_control("Passo", list(range(len(PASSOS))), default=passo,
                               format_func=lambda i: f"{marca[stp[PASSOS[i]]]} {i + 1}. {PASSOS[i]}",
                               label_visibility="collapsed", key=f"seg_{st.session_state.get('seg_gen', 0)}")
    if sel is not None and sel != passo:
        _ir_para(sel)
        st.rerun()

    e, d = st.columns([2.3, 1], gap="medium")
    with e, ui.card(key_extra=f"passo{passo}"):
        nome = PASSOS[passo]
        st.markdown(f'<div class="oc-passo"><div><div class="passo-titulo">Passo {passo + 1} de {len(PASSOS)}</div>'
                    f'<div class="oc-titulo" style="font-size:1.35rem">{nome}</div>'
                    f'<div class="oc-subt">{DESCRICAO[nome]}</div></div>{ui.ilu(ILU_PASSO[nome])}</div>',
                    unsafe_allow_html=True)
        FUNCOES[passo](pj)
        st.write("")
        b1, _, b2 = st.columns([1, 2, 1])
        if passo > 0 and b1.button("← Anterior", width="stretch"):
            _ir_para(passo - 1)
            st.rerun()
        if passo < len(PASSOS) - 1:
            if b2.button("Próximo →", type="primary", width="stretch"):
                _ir_para(passo + 1)
                st.rerun()
        else:
            b2.page_link(ui.PAGINAS["painel"], label="Ver o painel", icon=":material/dashboard:")
    with d:
        painel_vivo(ui.contexto())
        st.download_button("Salvar projeto (.json)", para_json(pj), file_name=f"{_slug(pj['fazenda'].get('nome'))}.json",
                           mime="application/json", icon=":material/download:", width="stretch")
