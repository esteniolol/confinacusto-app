"""
ConfinaCusto — sistema de custos e viabilidade de confinamento bovino.
Disciplina Custos nos Agronegócios (UnB) · Marcos da Silva Oliveira e Ana Beatriz Liberal Dionizio.

Rodar:  python -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

import ui
from pages_analise import pagina_mapa, pagina_painel, pagina_simulador
from pages_projeto import _slug, pagina_cadastro, pagina_inicio, status_passos, tela_entrada
from pages_relatorios import pagina_relatorios
from projeto_io import para_json

st.set_page_config(page_title="ConfinaCusto", page_icon="🐂", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
ui.iniciar_estado()
ui.novo_ciclo()

P = {
    "inicio": st.Page(pagina_inicio, title="Início", icon=":material/home:", url_path="inicio", default=True),
    "cadastro": st.Page(pagina_cadastro, title="Cadastro", icon=":material/edit_note:", url_path="cadastro"),
    "painel": st.Page(pagina_painel, title="Painel", icon=":material/dashboard:", url_path="painel"),
    "mapa": st.Page(pagina_mapa, title="Mapa dos currais", icon=":material/grid_view:", url_path="mapa"),
    "simulador": st.Page(pagina_simulador, title="Simulador", icon=":material/tune:", url_path="simulador"),
    "relatorios": st.Page(pagina_relatorios, title="Relatórios", icon=":material/description:", url_path="relatorios"),
}
ui.PAGINAS.update(P)
MENU = {"Projeto": ["inicio", "cadastro"], "Acompanhamento": ["painel", "mapa", "simulador"],
        "Emitir": ["relatorios"]}

ROTULO = {"mapa": "Mapa", "simulador": "Simulador"}
ROTULO_MOB = {"inicio": "Início", "cadastro": "Cadastro", "painel": "Painel", "mapa": "Mapa", "simulador": "Simular",
              "relatorios": "Relatórios"}

atual = st.navigation(list(P.values()), position="hidden")

if not st.session_state.get("escolheu"):      # primeira decisão: exemplo pronto ou projeto novo
    tela_entrada()
    st.stop()

with st.sidebar:
    pj = st.session_state.projeto
    c = ui.contexto()
    stp = status_passos(pj, c.pend)
    feitos = sum(1 for v in stp.values() if v == "ok")
    f = pj["fazenda"]
    local = " · ".join(x for x in (f.get("ciclo"), "-".join(y for y in (f.get("municipio"), f.get("uf")) if y)) if x)
    st.markdown(
        f'<div class="oc-marca">{ui.ilu("vaca")[:-1]} style="height:26px"><div>Confina<span>Custo</span></div></div>'
        f'<div class="oc-perfil"><div class="oc-avatar" style="--p:{round(100 * feitos / len(stp))}">'
        f'<div>{ui.ilu("vaca")}</div></div>'
        f'<div class="oc-nome">{ui.nome_fazenda(pj)}</div><div class="oc-sub">{local or "Novo projeto"}</div>'
        f'<div class="oc-prog">Cadastro <b>{feitos} de {len(stp)}</b> passos</div></div>',
        unsafe_allow_html=True)
    with st.container(key="navbox"):
        for secao, chaves in MENU.items():
            st.markdown(f'<div class="oc-secao">{secao}</div>', unsafe_allow_html=True)
            for k in chaves:
                pg = P[k]
                with st.container(key=f"nav-{'on' if pg.url_path == atual.url_path else 'off'}-{k}"):
                    st.page_link(pg, label=ROTULO.get(k, pg.title), icon=pg.icon)
    st.write("")
    st.download_button("Salvar projeto", para_json(pj), file_name=f"{_slug(f.get('nome'))}.json",
                       mime="application/json", icon=":material/save:", width="stretch", key="dl_sidebar")
    st.markdown(f'<div class="oc-rodape"><div class="cena">{ui.ilu("boi", "b")}{ui.ilu("milho", "m")}</div>'
                f'<div class="chao"></div><p>Custos nos Agronegócios · UnB<br>Marcos da Silva Oliveira<br>Ana Beatriz Liberal Dionizio</p></div>',
                unsafe_allow_html=True)

# barra de navegação do celular (só aparece em telas pequenas)
with st.container(key="mobnav"):
    for k in ("inicio", "cadastro", "painel", "mapa", "simulador", "relatorios"):
        pg = P[k]
        with st.container(key=f"mob-{'on' if pg.url_path == atual.url_path else 'off'}-{k}"):
            st.page_link(pg, label=ROTULO_MOB[k], icon=pg.icon)

atual.run()
