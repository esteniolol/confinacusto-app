"""Telas de análise: Painel, Mapa do confinamento e Simulador."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.colors import sample_colorscale

import ui
from engine import Cenario, _f, calcular, capacidade_total, monte_carlo, tornado
from ui import AMBAR, AZUL, BENCH, CINZA, TEAL, VERDE, VERDE_ESC, VERMELHO, brl, layout, md, mi, num, pct

CORES_SERIE = [VERDE, AMBAR, TEAL, AZUL, CINZA, VERMELHO]


# ============================================================================
# PAINEL
# ============================================================================
def pagina_painel():
    st.session_state.last_page = "painel"
    c = ui.contexto()
    ui.topo("Acompanhamento", "Painel do confinamento", ui.nome_fazenda(c.pj))
    ui.exige_calculo(c)
    r, p, pj = c.r, c.r["p"], c.pj
    f = pj["fazenda"]
    tags = [f.get("ciclo") or "", f"{num(p['dias'])} dias de cocho", f"GMD {num(p['gmd'], 2)} kg/dia",
            f"venda a {brl(p['pvenda'], 2)}/@"]
    html = "".join(f'<span class="tag">{t}</span>' for t in tags if t)
    if c.pend.get("Investimento"):
        html += '<span class="tag warn">Sem investimento cadastrado</span>'
    st.markdown(html, unsafe_allow_html=True)

    # ---- cartões de destaque -------------------------------------------------
    cap = capacidade_total(pj)
    ocup = sum(int(_f(x.get("animais"))) for x in pj["currais"])
    n_cur = len(pj["currais"])
    h = st.columns(3)
    h[0].markdown(ui.hero("Resultado por boi", brl(r["res_op_cab"]),
                          f"{mi(r['res_op'])} no ano", "boi", "ouro"),
                  unsafe_allow_html=True)
    h[1].markdown(ui.hero("Preço de equilíbrio", f"{brl(r['pe_ct'], 2)}/@",
                          f"margem de segurança {pct(r['margem_seg'])}", "milho", "escuro"),
                  unsafe_allow_html=True)
    if n_cur:
        cel = min(n_cur, 24)
        on = round(cel * (ocup / cap)) if cap and ocup else cel
        h[2].markdown(ui.hero("Bois no giro", num(p["cab"]), f"{num(cap)} vagas em {n_cur} currais",
                              tema="escuro", pontos=(cel, on, 6 if cel > 12 else 4)), unsafe_allow_html=True)
    else:
        h[2].markdown(ui.hero("Bois no giro", num(p["cab"]), "cadastre os currais para ver o mapa", "cerca"),
                      unsafe_allow_html=True)
    st.write("")

    k = st.columns(5)
    k[0].metric("Custo da @", brl(r["cprod_coe"], 2), border=True,
                help=f"COE sem a compra do boi, dividido pelas @ produzidas. Só nutrição e sanidade: "
                     f"{brl(r['cprod_mb'], 2)}.")
    k[1].metric("Diária/cabeça", brl(r["diaria_op"], 2),
                delta=f"{num(r['diaria_op'] - BENCH['Goiás'], 2)} vs. GO", delta_color="inverse", border=True,
                help="Custo operacional por cabeça-dia, sem o boi magro. Referência: Confina Brasil 2025 (Scot).")
    k[2].metric("VPL (10 anos)", mi(r["vpl"]) if r.get("vpl") is not None else "—", border=True)
    k[3].metric("TIR", pct(r["tir"]) if r.get("tir") is not None else "—", border=True)
    k[4].metric("Payback", f"{num(r['payback'], 1)} anos" if r.get("payback") else "> 10 anos",
                delta=f"{num(r['payback_fixo'], 1)} s/ giro" if r.get("payback_fixo") else None,
                delta_color="off", border=True)

    st.write("")
    e, d = st.columns([1.55, 1], gap="medium")
    with e, ui.card():
        ui.titulo_card("Para onde vai o dinheiro de cada boi", "R$ por boi vendido, da receita ao lucro")
        cv = r["cab_vend"]
        cc = r["custos"]
        demais = r["coe"] - cc["rep"] - cc["aq"] - cc["pasto"] - cc["alim"] - cc["fun"] - r["mao_de_obra"]
        etapas = [("Receita", r["receita"] / cv, "absolute"),
                  ("Boi magro,<br>frete, pasto", -(cc["rep"] + cc["aq"] + cc["pasto"]) / cv, "relative"),
                  ("Alimen-<br>tação", -cc["alim"] / cv, "relative"),
                  ("Mão de<br>obra", -r["mao_de_obra"] / cv, "relative"),
                  ("Diesel,<br>energia…", -demais / cv, "relative"),
                  ("Funrural", -cc["fun"] / cv, "relative"),
                  ("Depre-<br>ciação", -r["dep"] / cv, "relative"),
                  ("Lucro<br>antes IR", None, "total")]
        fig = go.Figure(go.Waterfall(
            x=[x[0] for x in etapas], y=[x[1] if x[1] is not None else 0 for x in etapas],
            measure=[x[2] for x in etapas],
            text=[brl(x[1]) if x[1] is not None else brl(r["lucro_cab"]) for x in etapas], textposition="outside",
            connector=dict(line=dict(color="#D3DED9", width=1, dash="dot")),
            increasing=dict(marker=dict(color=VERDE)), decreasing=dict(marker=dict(color=AMBAR)),
            totals=dict(marker=dict(color=TEAL))))
        lo = min(0, r["lucro_cab"] * 1.3)
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f", range=[lo, r["receita"] / cv * 1.14])
        fig.update_xaxes(tickangle=0, tickfont=dict(size=11))
        fig.update_traces(cliponaxis=False, textfont=dict(size=11))
        st.plotly_chart(layout(fig, 360), config={"displayModeBar": False}, key="cascata")

    with d, ui.card():
        ui.titulo_card("Diária comparada ao mercado", "R$/cabeça/dia, sem o boi magro")
        rot = "Este projeto"
        nomes = [rot] + list(BENCH)
        vals = [r["diaria_op"]] + list(BENCH.values())
        ordem = np.argsort(vals)
        curto = {"Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "São Paulo": "SP", "Goiás": "GO",
                 "Média Brasil": "Brasil", "Mato Grosso": "MT", rot: "Projeto"}
        cores = [AMBAR if nomes[i] == rot else (TEAL if nomes[i] == "Goiás" else VERDE) for i in ordem]
        fig = go.Figure(go.Bar(x=[curto[nomes[i]] for i in ordem], y=[vals[i] for i in ordem], marker_color=cores,
                               width=.42, text=[num(vals[i], 2) for i in ordem], textposition="outside",
                               customdata=[nomes[i] for i in ordem],
                               hovertemplate="%{customdata}<br>R$ %{y:.2f}/cab/dia<extra></extra>"))
        fig.update_yaxes(range=[0, max(vals) * 1.22], tickprefix="R$ ")
        fig.update_traces(cliponaxis=False, textfont=dict(size=11), constraintext="none")
        st.plotly_chart(layout(fig, 336), config={"displayModeBar": False})
        st.markdown('<div class="nota">Mercado: Benchmarking Confina Brasil 2025, Scot Consultoria '
                    '(184 confinamentos). Em verde-água, Goiás.</div>', unsafe_allow_html=True)

    st.write("")
    e, d = st.columns([1, 1.55], gap="medium")
    with e, ui.card():
        ui.titulo_card("Composição do custo", "custo total por boi vendido")
        cv = r["cab_vend"]
        grupos = {"Boi magro e aquisição": r["custos"]["rep"] + r["custos"]["aq"] + r["custos"]["pasto"],
                  "Alimentação": r["custos"]["alim"], "Mão de obra": r["mao_de_obra"],
                  "Outros operacionais": r["coe"] - r["custos"]["rep"] - r["custos"]["aq"] - r["custos"]["pasto"]
                  - r["custos"]["alim"] - r["mao_de_obra"],
                  "Depreciação e oportunidade": r["dep"] + r["op_inv"] + r["op_giro"]}
        grupos = {k: v for k, v in grupos.items() if v > 0}
        fig = go.Figure(go.Pie(labels=list(grupos), values=[v / cv for v in grupos.values()], hole=.62, sort=False, domain=dict(x=[0.1, 0.9], y=[0.34, 1]),
                               marker=dict(colors=[VERDE, AMBAR, TEAL, AZUL, CINZA], line=dict(color="#fff", width=3)),
                               textinfo="percent", textfont=dict(color="#fff", size=11), direction="clockwise",
                               hovertemplate="%{label}<br>R$ %{value:,.0f}/boi<extra></extra>"))
        fig.add_annotation(text=f"<b>{brl(sum(grupos.values()) / cv)}</b><br><span style='font-size:11px'>por boi"
                                f"</span>", showarrow=False, x=0.5, y=0.67, font=dict(size=16, color="#23332F"))
        fig = layout(fig, 360, legenda=True)
        fig.update_layout(legend=dict(orientation="h", y=0, yanchor="bottom", x=0.5, xanchor="center",
                                      font=dict(size=11)), margin=dict(t=10, b=0))
        st.plotly_chart(fig, config={"displayModeBar": False})

    with d, ui.card():
        if pj["vendas"]:
            ui.titulo_card("Vendas realizadas × preço de equilíbrio", "preço médio da @ em cada data de embarque")
            v = pd.DataFrame(pj["vendas"])
            v["data"] = pd.to_datetime(v["data"])
            v["valor"] = v["preco_arroba"] * v["animais"]
            g = v.groupby("data").agg(animais=("animais", "sum"), valor=("valor", "sum"),
                                      comp=("comprador", lambda s: ", ".join(dict.fromkeys(x or "—" for x in s))))
            g["preco"] = g["valor"] / g["animais"]
            ys = list(g["preco"]) + [r["pe_ct"], r["pe_coe"]]
            lo = min(ys) * 0.94
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=g.index, y=[r["pe_ct"]] * len(g), mode="lines", name="Equilíbrio (custo total)",
                                     line=dict(color=VERDE, width=2, dash="dot"), hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=g.index, y=g["preco"], mode="lines+markers", name="Preço obtido", line=dict(color=AMBAR, width=3, shape="spline", smoothing=0.6),
                fill="tonexty", fillcolor="rgba(217,166,46,.13)",
                marker=dict(size=np.sqrt(g["animais"].astype(float)) * 2.2 + 6, color="#fff",
                            line=dict(color=AMBAR, width=2.5)),
                customdata=np.stack([g["animais"], g["comp"]], axis=1),
                hovertemplate="%{x|%d/%m}<br><b>R$ %{y:.2f}/@</b><br>%{customdata[0]} bois · %{customdata[1]}"
                              "<extra></extra>"))
            fig.add_annotation(x=g.index[0], y=r["pe_ct"], text=f"equilíbrio {brl(r['pe_ct'], 2)}", showarrow=False,
                               yshift=-12, xanchor="left", font=dict(size=11, color=VERDE))
            fig.update_yaxes(tickprefix="R$ ", range=[lo, max(ys) * 1.05])
            fig.update_xaxes(tickformat="%d/%m", showgrid=False)
            st.plotly_chart(layout(fig, 336, legenda=True), config={"displayModeBar": False})
            st.markdown(f'<div class="nota">Tamanho do ponto = nº de bois embarcados. '
                        f'{num(v["animais"].sum())} bois vendidos.</div>', unsafe_allow_html=True)
        else:
            ui.titulo_card("Vendas realizadas × preço de equilíbrio")
            ui.vazio("Nenhuma venda cadastrada ainda", "Cadastre os lotes vendidos (passo 9) para comparar o preço "
                     "obtido com o preço de equilíbrio.", "boi")

    st.write("")
    with ui.card():
        e, d = st.columns([1.3, 1], gap="large")
        with e:
            ui.titulo_card("Custo da @ produzida — três visões", "do que o sistema de rebanho mostra ao custo total")
            visoes = [("Só nutrição e sanidade", r["cprod_mb"]), ("Operacional completo", r["cprod_coe"]),
                      ("Custo total", r["cprod_ct"])]
            fig = go.Figure(go.Bar(y=[x[0] for x in visoes][::-1], x=[x[1] for x in visoes][::-1], orientation="h",
                                   cliponaxis=False, width=.5, marker_color=[VERDE, TEAL, CINZA],
                                   text=[brl(x[1], 2) for x in visoes][::-1], textposition="outside"))
            fig.add_vline(x=p["pvenda"], line=dict(color=AMBAR, dash="dash", width=2),
                          annotation_text=f"venda {brl(p['pvenda'], 2)}/@", annotation_position="top",
                          annotation_font=dict(size=11, color=AMBAR))
            fig.update_xaxes(tickprefix="R$ ", range=[0, max(p["pvenda"], r["cprod_ct"]) * 1.2])
            st.plotly_chart(layout(fig, 230), config={"displayModeBar": False})
        with d:
            st.write("")
            st.markdown('<div class="nota">Só nutrição e sanidade: o que os sistemas de gestão de rebanho costumam '
                        'mostrar (+ pasto pré-confinamento). Operacional completo: + mão de obra, diesel, energia, '
                        'rateios e Funrural. Custo total: + depreciação e custo de oportunidade.</div>',
                        unsafe_allow_html=True)
            if r["cprod_mb"] > 0:
                st.markdown(f'<div class="insight">Olhando só nutrição e sanidade, a @ produzida custa '
                            f'<b>{brl(r["cprod_mb"], 2)}</b>. Com todos os custos, custa <b>{brl(r["cprod_ct"], 2)}</b>'
                            f' — {pct(r["cprod_ct"] / r["cprod_mb"] - 1, 0)} a mais.</div>', unsafe_allow_html=True)


# ============================================================================
# MAPA
# ============================================================================
ESC_VERDE = [[0, "rgb(214,232,226)"], [0.5, "rgb(122,166,155)"], [1, "rgb(47,74,69)"]]
ESC_OURO = [[0, "rgb(251,239,208)"], [0.5, "rgb(232,190,92)"], [1, "rgb(176,124,22)"]]
ESC_MARGEM = [[0, "rgb(217,120,95)"], [0.5, "rgb(244,238,223)"], [1, "rgb(43,150,135)"]]
ESC_MORTE = [[0, "rgb(251,228,219)"], [1, "rgb(194,86,61)"]]
METRICAS = {
    "Ocupação": ("ocupacao", ESC_VERDE, lambda v: pct(v, 0)),
    "Dias de cocho": ("dias_cocho", ESC_VERDE, lambda v: f"{num(v)} d"),
    "GMD": ("gmd", ESC_VERDE, lambda v: f"{num(v, 2)} kg"),
    "Custo acumulado/boi": ("custo_cab", ESC_OURO, lambda v: brl(v)),
    "Margem projetada/boi": ("margem_proj", ESC_MARGEM, lambda v: brl(v)),
    "Mortes": ("mortes", ESC_MORTE, lambda v: num(v)),
}


def _ret_arred(x0, y0, x1, y1, r=0.14):
    """Caminho SVG de um retângulo com cantos arredondados (para os currais do mapa)."""
    return (f"M{x0 + r},{y0} L{x1 - r},{y0} Q{x1},{y0} {x1},{y0 + r} L{x1},{y1 - r} Q{x1},{y1} {x1 - r},{y1} "
            f"L{x0 + r},{y1} Q{x0},{y1} {x0},{y1 - r} L{x0},{y0 + r} Q{x0},{y0} {x0 + r},{y0} Z")
CAMPOS = ["curral", "linha", "capacidade", "area_ha", "animais", "sexo", "dias_cocho", "gmd", "peso_entrada",
          "peso_proj", "custo_cab", "mortes", "aquisicao", "frete", "outros_aq", "custo_pasto", "nutricao", "sanidade"]


def _currais_df(c):
    df = pd.DataFrame([{k: cur.get(k) for k in CAMPOS} for cur in c.pj["currais"]], columns=CAMPOS)
    for col in CAMPOS:
        if col != "sexo":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["animais"] = df["animais"].fillna(0)
    df["capacidade"] = df["capacidade"].fillna(0)
    df["linha"] = df["linha"].fillna(1).astype(int)
    df["sexo"] = df["sexo"].fillna("M")
    df["mortes"] = df["mortes"].fillna(0)
    p = c.r["p"]
    fixos_boi = (c.r["fixos"] + c.r["dep"]) / c.r["cab_vend"] if c.r["cab_vend"] else 0
    df["ocupacao"] = np.where(df["capacidade"] > 0, df["animais"] / df["capacidade"].replace(0, np.nan), np.nan)
    receita = df["peso_proj"] * p["rc"] / 15 * p["pvenda"]
    df["margem_proj"] = np.where((df["sexo"] == "M") & df["custo_cab"].notna(), receita - df["custo_cab"] - fixos_boi,
                                 np.nan)
    df["fixos_boi"] = fixos_boi
    return df.sort_values(["linha", "curral"]).reset_index(drop=True)


def _figura_mapa(df, chave, escala, fmt, selecionado):
    fig = go.Figure()
    vals = df[chave].astype(float)
    validos = vals.dropna()
    lo, hi = (validos.min(), validos.max()) if len(validos) else (0, 1)
    if chave == "margem_proj":
        m = max(abs(lo), abs(hi)) or 1
        lo, hi = -m, m
    span = (hi - lo) or 1

    linhas = sorted(df["linha"].unique())
    n_lin = len(linhas)
    largura = max(df.groupby("linha").size().max(), 1) * 1.1
    pos, y_lin = {}, {}
    for i, lin in enumerate(linhas):
        y0 = (n_lin - 1 - i) * 1.55
        y_lin[lin] = y0
        for j, (_, row) in enumerate(df[df["linha"] == lin].iterrows()):
            pos[row.name] = (j * 1.1, y0)
    # corredores de trato entre pares de linhas (linha 1 e 2 dividem o mesmo cocho, e assim por diante)
    for i in range(0, n_lin - 1, 2):
        y_mid = (y_lin[linhas[i]] + y_lin[linhas[i + 1]] + 1.0) / 2
        fig.add_shape(type="path", path=_ret_arred(-0.15, y_mid - 0.17, largura - 0.25, y_mid + 0.17, 0.12),
                      fillcolor="#F4EAD2", line=dict(width=0))
        fig.add_annotation(x=(largura - 0.4) / 2, y=y_mid, text="CORREDOR DE TRATO · LINHAS DE COCHO",
                           showarrow=False, font=dict(size=11, color="#A07A26"))
    for i, lin in enumerate(linhas):
        abaixo = i % 2 == 1          # a segunda linha de cada par fica do outro lado do corredor
        fig.add_annotation(x=-0.15, y=y_lin[lin] - 0.12 if abaixo else y_lin[lin] + 1.07, text=f"LINHA {lin}",
                           showarrow=False, xanchor="left", yanchor="top" if abaixo else "bottom",
                           font=dict(size=11, color="#5D6B64"))

    xs, ys, ids, hov = [], [], [], []
    for idx, row in df.iterrows():
        x0, y0 = pos[idx]
        n = int(row["curral"])
        v = row[chave]
        vazio = row["animais"] == 0
        cor = ("#F1F5F3" if vazio else "#E6ECE9") if (vazio or pd.isna(v)) else \
            sample_colorscale(escala, [0.08 + 0.84 * (v - lo) / span])[0]
        borda = dict(color=AMBAR, width=4) if n == selecionado else dict(color="#FFFFFF", width=2)
        fig.add_shape(type="path", path=_ret_arred(x0, y0, x0 + 1.0, y0 + 1.0), fillcolor=cor, line=borda,
                      layer="below")
        escuro = (not vazio and not pd.isna(v) and (v - lo) / span > 0.55 and chave != "margem_proj")
        tc = "#FFFFFF" if escuro else "#1C2B24"
        cap = int(row["capacidade"])
        fig.add_annotation(x=x0 + 0.5, y=y0 + 0.74, text=f"<b>C{n}</b>", showarrow=False, font=dict(size=15, color=tc))
        fig.add_annotation(x=x0 + 0.5, y=y0 + 0.47, showarrow=False, font=dict(size=11, color=tc),
                           text=f"{int(row['animais'])}/{cap if cap else '?'}")
        txt = "vazio" if vazio else ("fêmeas" if row["sexo"] == "F" and chave == "margem_proj"
                                     else ("—" if pd.isna(v) else fmt(v)))
        fig.add_annotation(x=x0 + 0.5, y=y0 + 0.22, showarrow=False, font=dict(size=11, color=tc), text=txt)
        xs.append(x0 + 0.5)
        ys.append(y0 + 0.5)
        ids.append(n)
        hov.append(f"Curral {n} · {int(row['animais'])} animais")
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(size=60, opacity=0, symbol="square"),
                             customdata=ids, hovertext=hov, hoverinfo="text"))
    top = (n_lin - 1) * 1.55 + 1.25
    fig.update_xaxes(visible=False, range=[-0.3, max(largura, 6)])
    fig.update_yaxes(visible=False, range=[-0.45, top], scaleanchor="x", scaleratio=1)
    fig.update_layout(dragmode=False, clickmode="event+select")
    return layout(fig, int(70 + 150 * n_lin))


def pagina_mapa():
    st.session_state.last_page = "mapa"
    c = ui.contexto()
    ui.topo("Acompanhamento", "Mapa dos currais", f"{ui.nome_fazenda(c.pj)} · clique num curral para abrir a ficha",
            "cerca")
    if not c.pj["currais"]:
        ui.vazio("Nenhum curral cadastrado ainda", "Cadastre os currais no passo 2 do cadastro.", "cerca")
        st.page_link(ui.PAGINAS["cadastro"], label="Cadastrar currais", icon=":material/edit_note:")
        st.stop()
    ui.exige_calculo(c)
    df = _currais_df(c)
    with ui.card():
        ui.titulo_card("Planta do confinamento", f"{len(df)} currais em {df['linha'].nunique()} linha(s) · colorir por:")
        disponiveis = [k for k, (col, *_) in METRICAS.items() if df[col].notna().any() and (col != "mortes" or df[col].sum())]
        escolha = st.segmented_control("Colorir por", disponiveis, default=disponiveis[0], label_visibility="collapsed")
        chave, escala, fmt = METRICAS[escolha or disponiveis[0]]
        ocupados = df[df["animais"] > 0]
        sel = st.session_state.get("curral_sel")
        if sel not in set(df["curral"]):
            sel = int(ocupados.sort_values("animais", ascending=False)["curral"].iloc[0]) if len(ocupados) \
                else int(df["curral"].iloc[0])

        ev = st.plotly_chart(_figura_mapa(df, chave, escala, fmt, sel), key="mapa", on_select="rerun",
                             selection_mode="points", config={"displayModeBar": False})
    pts = (ev or {}).get("selection", {}).get("points", []) if ev else []
    if pts:
        cd = pts[0]["customdata"]
        novo = int(cd[0] if isinstance(cd, list) else cd)
        if novo != sel:
            st.session_state["curral_sel"] = novo
            st.rerun()

    k = st.columns(4)
    k[0].metric("Animais nos currais", num(df["animais"].sum()), border=True)
    k[1].metric("Ocupação", pct(df["animais"].sum() / df["capacidade"].sum(), 0) if df["capacidade"].sum() else "—",
                border=True)
    machos = ocupados[(ocupados["sexo"] == "M") & ocupados["dias_cocho"].notna()]
    k[2].metric("Dias de cocho (média)", num(np.average(machos["dias_cocho"], weights=machos["animais"]), 0)
                if len(machos) else "—", border=True)
    k[3].metric("Mortes", num(df["mortes"].sum()), border=True)

    if df["mortes"].sum() > 0:
        pior = df.loc[df["mortes"].idxmax()]
        if pior["mortes"] >= max(3, 0.3 * df["mortes"].sum()):
            st.markdown(f'<div class="insight"><b>Curral {int(pior["curral"])}:</b> concentra {int(pior["mortes"])} das '
                        f'{int(df["mortes"].sum())} mortes registradas — vale investigar.</div>', unsafe_allow_html=True)

    st.write("")
    with ui.card():
        ui.titulo_card(f"Ficha do curral {sel}", "clique em outro curral no mapa para trocar")
        row = df[df["curral"] == sel].iloc[0]
        if row["animais"] == 0:
            st.info("Curral vazio no momento.")
        else:
            f = st.columns(6)
            f[0].metric("Animais", f"{int(row['animais'])} / {int(row['capacidade']) or '?'}", border=True)
            f[1].metric("Dias de cocho", num(row["dias_cocho"], 0), border=True)
            f[2].metric("GMD", f"{num(row['gmd'], 2)} kg", border=True)
            f[3].metric("Peso (kg)", f"{num(row['peso_entrada'])} → {num(row['peso_proj'])}", border=True)
            f[4].metric("Custo acumulado/boi", brl(row["custo_cab"]) if pd.notna(row["custo_cab"]) else "—", border=True)
            f[5].metric("Margem proj./boi", brl(row["margem_proj"]) if pd.notna(row["margem_proj"]) else
                        ("fêmeas" if row["sexo"] == "F" else "—"), border=True,
                        help="Receita no peso projetado, menos o custo acumulado e a parcela de fixos e depreciação por boi.")
            e, d = st.columns([1.2, 1])
            with e:
                if pd.notna(row.get("aquisicao")):
                    partes = [("Boi magro", row["aquisicao"]), ("Frete e outros", (row["frete"] or 0) + (row["outros_aq"] or 0)),
                              ("Pasto pré-confinamento", row["custo_pasto"]), ("Nutrição no cocho", row["nutricao"]),
                              ("Sanidade", row["sanidade"]), ("Fixos + depreciação (rateio)", row["fixos_boi"])]
                    cores = [VERDE, CINZA, TEAL, AMBAR, AZUL, "#E8C66E"]
                elif pd.notna(row["custo_cab"]):
                    partes = [("Custo acumulado", row["custo_cab"]), ("Fixos + depreciação (rateio)", row["fixos_boi"])]
                    cores = [VERDE, AMBAR]
                else:
                    partes = []
                if partes:
                    partes = [(a, _f(b)) for a, b in partes]
                    fig = go.Figure(go.Bar(x=[x[1] for x in partes], y=[x[0] for x in partes], orientation="h",
                                           marker_color=cores, text=[brl(x[1]) for x in partes], textposition="outside"))
                    fig.update_yaxes(autorange="reversed")
                    fig.update_xaxes(tickprefix="R$ ", range=[0, max(x[1] for x in partes) * 1.25])
                    st.plotly_chart(layout(fig, 280), config={"displayModeBar": False})
            with d:
                p = c.r["p"]
                linhas = ["**Leitura rápida**"]
                if pd.notna(row["peso_proj"]):
                    rec = row["peso_proj"] * p["rc"] / 15 * p["pvenda"]
                    linhas.append(f"- Entrou com **{num(row['peso_entrada'])} kg** e está projetado em "
                                  f"**{num(row['peso_proj'])} kg** ({num(row['dias_cocho'])} dias).")
                    linhas.append(f"- No preço atual ({brl(p['pvenda'], 2)}/@) cada boi vale **{brl(rec)}**.")
                if pd.notna(row["custo_cab"]):
                    linhas.append(f"- Custo acumulado de **{brl(row['custo_cab'])}** por boi, mais **{brl(row['fixos_boi'])}** "
                                  f"de mão de obra, diesel, energia e depreciação rateados.")
                linhas.append(f"- Mortes: **{int(row['mortes'])}**.")
                md("  \n".join(linhas))

    st.write("")
    with ui.card():
        ui.titulo_card("Todos os currais")
        tab = df[["curral", "linha", "animais", "capacidade", "ocupacao", "dias_cocho", "gmd", "peso_entrada", "peso_proj",
                  "custo_cab", "margem_proj", "mortes"]]
        st.dataframe(tab, hide_index=True, column_config={
            "curral": st.column_config.NumberColumn("Curral", format="%d"),
            "linha": st.column_config.NumberColumn("Linha", format="%d"),
            "animais": st.column_config.NumberColumn("Animais", format="%d"),
            "capacidade": st.column_config.NumberColumn("Capacidade", format="%d"),
            "ocupacao": st.column_config.ProgressColumn("Ocupação", min_value=0, max_value=1.2, format="percent"),
            "dias_cocho": st.column_config.NumberColumn("Dias", format="%.0f"),
            "gmd": st.column_config.NumberColumn("GMD (kg)", format="%.2f"),
            "peso_entrada": st.column_config.NumberColumn("Entrada (kg)", format="%.0f"),
            "peso_proj": st.column_config.NumberColumn("Projetado (kg)", format="%.0f"),
            "custo_cab": st.column_config.NumberColumn("Custo/boi", format="R$ %.0f"),
            "margem_proj": st.column_config.NumberColumn("Margem proj./boi", format="R$ %.0f"),
            "mortes": st.column_config.NumberColumn("Mortes", format="%d")})
    st.page_link(ui.PAGINAS["cadastro"], label="Editar currais no cadastro", icon=":material/edit_note:")


# ============================================================================
# SIMULADOR
# ============================================================================
def _padroes(c):
    p = c.r["p"]
    milho = next((i.preco_t for i in c.base.dieta if i.eh_milho), 0.0)
    return {"s_venda": float(p["pvenda"]), "s_compra": float(p["vcompra"]), "s_milho": round(milho * 0.06, 2),
            "s_gmd": float(p["gmd"]), "s_dias": int(p["dias"]), "s_mort": float(p["mort"] * 100),
            "s_cab": int(p["cab"]), "s_tma": float(p["tma"] * 100), "_milho_base_saca": round(milho * 0.06, 2)}


def _d(v, fmt, tol=0.5):
    return None if abs(v) < tol else fmt(v)


def pagina_simulador():
    st.session_state.last_page = "simulador"
    c = ui.contexto()
    ui.topo("Acompanhamento", "Simulador e risco", "Mexa nas premissas e veja o resultado mudar. A linha de base é o "
            "cenário cadastrado.", "trator")
    ui.exige_calculo(c)
    pad = _padroes(c)
    assinatura = tuple(round(v, 4) for v in pad.values())
    if st.session_state.get("_sim_base") != assinatura:          # o cadastro mudou: volta para a base
        for k, v in pad.items():
            st.session_state[k] = v
        st.session_state["_sim_base"] = assinatura

    cap = capacidade_total(c.pj)
    e, d = st.columns([1, 2.3], gap="large")
    with e, ui.card():
        st.markdown('<div class="passo-titulo">Mercado</div>', unsafe_allow_html=True)
        st.slider("Preço de venda (R$/@)", round(pad["s_venda"] * 0.6, 2), round(pad["s_venda"] * 1.4, 2) + 1,
                  key="s_venda", step=0.01, format="%.2f")
        st.slider("Boi magro (R$/cabeça)", float(round(pad["s_compra"] * 0.6)), float(round(pad["s_compra"] * 1.4)) + 1.0,
                  key="s_compra", step=0.5, format="%.0f")
        tem_milho = pad["_milho_base_saca"] > 0
        if tem_milho:
            st.slider("Milho (R$/saca de 60 kg)", float(round(pad["_milho_base_saca"] * 0.5, 2)),
                      float(round(pad["_milho_base_saca"] * 1.8, 2)), key="s_milho", step=0.01, format="%.2f")
        st.markdown('<div class="passo-titulo">Desempenho</div>', unsafe_allow_html=True)
        st.slider("GMD (kg/dia)", 0.5, float(max(2.5, pad["s_gmd"] * 1.3)), key="s_gmd", step=0.01)
        st.slider("Dias de cocho", max(20, int(pad["s_dias"] * 0.5)), int(pad["s_dias"] * 2) + 1, key="s_dias", step=1)
        st.slider("Mortalidade (%)", 0.0, float(max(5.0, pad["s_mort"] * 3)), key="s_mort", step=0.01, format="%.2f")
        st.markdown('<div class="passo-titulo">Escala e capital</div>', unsafe_allow_html=True)
        st.slider("Bois por ciclo", max(10, int(pad["s_cab"] * 0.2)), int(max(cap * 1.2, pad["s_cab"] * 1.5)) + 1,
                  key="s_cab", step=1)
        st.slider("TMA (% a.a.)", 0.0, 25.0, key="s_tma", step=0.5)

        def _reset():
            for k, v in _padroes(ui.contexto()).items():
                st.session_state[k] = v

        st.button("Voltar ao cenário cadastrado", on_click=_reset, width="stretch")

    ss = st.session_state
    cen = Cenario(pvenda=ss.s_venda, vcompra=float(ss.s_compra),
                  fator_milho=(ss.s_milho / pad["_milho_base_saca"]) if tem_milho else 1.0,
                  gmd=ss.s_gmd, dias=float(ss.s_dias), mort=ss.s_mort / 100, cab=float(ss.s_cab), tma=ss.s_tma / 100)
    r, b, base = calcular(c.base, cen), c.r, c.base

    with d:
        k = st.columns(3)
        k[0].metric("Resultado por boi", brl(r["res_op_cab"]), delta=_d(r["res_op_cab"] - b["res_op_cab"], brl), border=True)
        k[1].metric("Resultado no ano", mi(r["res_op"]), delta=_d(r["res_op"] - b["res_op"], mi, 5000), border=True)
        k[2].metric("Equilíbrio (R$/@)", brl(r["pe_ct"], 2), delta=_d(r["pe_ct"] - b["pe_ct"], lambda v: num(v, 2), 0.005),
                    delta_color="inverse", border=True)
        k = st.columns(3)
        k[0].metric("VPL (10 anos)", mi(r["vpl"]), delta=_d(r["vpl"] - b["vpl"], mi, 5000), border=True)
        k[1].metric("TIR", pct(r["tir"]), delta=None if r["tir"] is None or b["tir"] is None
                    else _d((r["tir"] - b["tir"]) * 100, lambda v: f"{num(v, 1)} p.p.", 0.05), border=True)
        k[2].metric("Payback", f"{num(r['payback'], 1)} anos" if r["payback"] else "> 10 anos",
                    delta=f"{num(r['payback_fixo'], 1)} s/ giro" if r["payback_fixo"] else None,
                    delta_color="off", border=True,
                    help="Com o capital de giro (compra dos bois e ração). Abaixo: só das instalações e máquinas.")

        st.write("")
        caixa = ui.card()
        a1, a2, a3 = caixa.tabs(["Risco (Monte Carlo)", "O que mais pesa (tornado)", "Fluxo de caixa"])
        with a1:
            with st.expander("Volatilidade das variáveis (premissas ajustáveis)"):
                v = st.columns(4)
                sd_v = v[0].number_input("Preço @ (±%)", 0.0, 40.0, 8.0, 1.0) / 100
                sd_c = v[1].number_input("Boi magro (±%)", 0.0, 40.0, 6.0, 1.0) / 100
                sd_m = v[2].number_input("Milho (±%)", 0.0, 60.0, 12.0, 1.0) / 100
                sd_g = v[3].number_input("GMD (±%)", 0.0, 40.0, 8.0, 1.0) / 100
            mc = monte_carlo(base, cen, n=10000, sd_venda=sd_v, sd_compra=sd_c, sd_milho=sd_m, sd_gmd=sd_g)
            res = mc["res_cab"]
            k = st.columns(2) + st.columns(2)      # 2 x 2: cabe o valor inteiro em tela de notebook
            k[0].metric("Chance de prejuízo", pct(mc["prob_prejuizo"]), border=True,
                        help="Proporção dos cenários com resultado operacional negativo por boi.")
            k[1].metric("Mediana por boi", brl(mc["p50"]), border=True)
            k[2].metric("Pior 5% por boi", brl(mc["p5"]), border=True)
            k[3].metric("Melhor 5% por boi", brl(mc["p95"]), border=True)
            hist, edges = np.histogram(res, bins=np.linspace(res.min(), res.max(), 60))
            centros = (edges[:-1] + edges[1:]) / 2
            fig = go.Figure(go.Bar(x=centros, y=hist, width=np.diff(edges), marker_line_width=0,
                                   marker_color=np.where(centros < 0, VERMELHO, VERDE),
                                   hovertemplate="R$ %{x:,.0f}/boi<br>%{y} cenários<extra></extra>"))
            fig.update_traces(marker_cornerradius=2)
            fig.add_vline(x=0, line=dict(color=VERDE_ESC, width=1.5))
            fig.add_vline(x=mc["p50"], line=dict(color=AMBAR, dash="dash"), annotation_text="mediana",
                          annotation_font=dict(color=AMBAR, size=11))
            fig.update_xaxes(tickprefix="R$ ", title="Resultado operacional por boi")
            fig.update_yaxes(title="Cenários")
            st.plotly_chart(layout(fig, 320), config={"displayModeBar": False})
            st.markdown('<div class="nota">10.000 cenários sorteados ao redor do cenário escolhido (distribuição normal, '
                        'variáveis independentes).</div>', unsafe_allow_html=True)
        with a2:
            tor = tornado(base, cen, 0.10)
            bc = r["res_op_cab"]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=[t[0] for t in tor], x=[t[1] - bc for t in tor], base=bc, orientation="h",
                                 name="−10%", marker_color=AMBAR))
            fig.add_trace(go.Bar(y=[t[0] for t in tor], x=[t[2] - bc for t in tor], base=bc, orientation="h",
                                 name="+10%", marker_color=VERDE))
            fig.add_vline(x=bc, line=dict(color=VERDE_ESC, width=1.5))
            fig.update_layout(barmode="overlay")
            fig.update_xaxes(tickprefix="R$ ", title="Resultado operacional por boi")
            st.plotly_chart(layout(fig, 330, legenda=True), config={"displayModeBar": False})
            maior = tor[-1]
            st.markdown(f'<div class="insight">Uma variação de 10% no <b>{maior[0].lower()}</b> move o resultado em '
                        f'<b>{brl((maior[2] - maior[1]) / 2)}</b> por boi — mais do que qualquer outro fator.</div>',
                        unsafe_allow_html=True)
        with a3:
            fl = r["fluxos"]
            anos = list(range(len(fl)))
            fig = go.Figure()
            fig.add_trace(go.Bar(x=anos, y=fl, name="Fluxo do ano", marker_color=[VERMELHO if f < 0 else VERDE for f in fl]))
            fig.add_trace(go.Scatter(x=anos, y=np.cumsum(fl), name="Acumulado", mode="lines+markers",
                                     line=dict(color=AMBAR, width=3, shape="spline")))
            fig.add_hline(y=0, line=dict(color="#9AA8A0", width=1))
            fig.update_yaxes(tickprefix="R$ ")
            fig.update_xaxes(title="Ano", dtick=1)
            st.plotly_chart(layout(fig, 320, legenda=True), config={"displayModeBar": False})
            st.markdown(f'<div class="nota">Ano 0: instalações e máquinas ({mi(base.desembolso_ano0)}) + capital de giro '
                        f'de um ciclo ({mi(r["giro"])}). O giro volta no ano 10.</div>', unsafe_allow_html=True)
