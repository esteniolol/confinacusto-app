"""Relatórios: custo de produção, DRE, fluxo de caixa e cadastros — em Excel ou prontos para imprimir."""
from __future__ import annotations

import datetime as dt
import html
import io

import numpy as np
import pandas as pd
import streamlit as st

import ui
from engine import (BASES, _f, capacidade_total, resumo_combustivel, resumo_dieta, resumo_investimento,
                    valor_anual_custos)
from ui import brl, num, pct


def _linha(nome, v, r, tipo=""):
    cv, av, ct = r["cab_vend"], r["cab_vend"] * r["arr_sai"], r["ct"]
    return {"Componente": nome, "Tipo": tipo, "R$/ano": v, "R$/boi": v / cv if cv else 0,
            "R$/@ vendida": v / av if av else 0, "% do CT": v / ct if ct else 0}


def tabelas(c) -> dict[str, pd.DataFrame]:
    r, p, pj = c.r, c.r["p"], c.pj
    cc = r["custos"]
    t = {}

    t["Indicadores"] = pd.DataFrame([
        ("Bois vendidos por ano", num(r["cab_vend"])), ("Arrobas vendidas por ano", num(r["cab_vend"] * r["arr_sai"])),
        ("Arrobas produzidas por ano", num(r["cab_vend"] * r["arr_prod"])),
        ("Receita bruta anual", brl(r["receita"])), ("Custo operacional efetivo (COE)", brl(r["coe"])),
        ("Custo operacional total (COT)", brl(r["cot"])), ("Custo total (CT)", brl(r["ct"])),
        ("Resultado operacional (caixa)", brl(r["res_op"])), ("Resultado operacional por boi", brl(r["res_op_cab"])),
        ("Lucro antes do IR", brl(r["lucro"])), ("Lucro econômico", brl(r["lucro_econ"])),
        ("Custo da @ produzida — só nutrição/sanidade", brl(r["cprod_mb"], 2)),
        ("Custo da @ produzida — COE", brl(r["cprod_coe"], 2)), ("Custo da @ produzida — CT", brl(r["cprod_ct"], 2)),
        ("Preço de equilíbrio — COE (R$/@)", brl(r["pe_coe"], 2)), ("Preço de equilíbrio — COT (R$/@)", brl(r["pe_cot"], 2)),
        ("Preço de equilíbrio — CT (R$/@)", brl(r["pe_ct"], 2)), ("Diária operacional (R$/cab/dia)", brl(r["diaria_op"], 2)),
        ("Margem de contribuição por boi", brl(r["mc_cab"])), ("Ponto de equilíbrio (bois/ano)", num(r["ponto_eq_cab"])),
        ("Margem de segurança", pct(r["margem_seg"])), ("VPL (10 anos, à TMA)", brl(r["vpl"])),
        ("TIR", pct(r["tir"])), ("Payback simples", f"{num(r['payback'], 1)} anos" if r["payback"] else "> 10 anos"),
        ("Payback descontado", f"{num(r['payback_desc'], 1)} anos" if r["payback_desc"] else "> 10 anos"),
        ("Payback só do investimento fixo", f"{num(r['payback_fixo'], 1)} anos" if r["payback_fixo"] else "—"),
    ], columns=["Indicador", "Valor"])

    linhas = [_linha("Reposição (boi magro)", cc["rep"], r, "Variável"),
              _linha("Frete e outros de aquisição", cc["aq"], r, "Variável"),
              _linha("Pasto pré-confinamento", cc["pasto"], r, "Variável"),
              _linha("Alimentação", cc["alim"], r, "Variável")]
    for lc, v in r["linhas"]:
        linhas.append(_linha(lc.item, v, r, lc.classe))
    linhas += [_linha("Funrural + Senar", cc["fun"], r, "Variável"),
               _linha("(=) COE — Custo operacional efetivo", r["coe"], r),
               _linha("Depreciação", r["dep"], r, "Fixo"),
               _linha("(=) COT — Custo operacional total", r["cot"], r),
               _linha("Custo de oportunidade do investimento", r["op_inv"], r, "Fixo"),
               _linha("Custo de oportunidade do capital de giro", r["op_giro"], r, "Variável"),
               _linha("(=) CT — Custo total", r["ct"], r),
               _linha("Custos variáveis", r["var"], r), _linha("Custos fixos", r["fix"], r)]
    t["Custo de produção"] = pd.DataFrame(linhas)

    cv = r["cab_vend"]
    var_desemb = r["var"] - r["op_giro"] - cc["fun"]
    dre = [("(+) Receita bruta", r["receita"]), ("(−) Funrural + Senar", -cc["fun"]),
           ("(=) Receita líquida", r["receita"] - cc["fun"]), ("(−) Custos variáveis", -var_desemb),
           ("(=) Margem de contribuição", r["receita"] - cc["fun"] - var_desemb),
           ("(−) Custos fixos desembolsáveis", -r["fixos"]), ("(=) Resultado operacional (caixa)", r["res_op"]),
           ("(−) Depreciação", -r["dep"]), ("(=) Lucro antes do IR", r["lucro"]),
           ("(−) Custo de oportunidade do capital", -(r["op_inv"] + r["op_giro"])), ("(=) Lucro econômico", r["lucro_econ"])]
    t["DRE"] = pd.DataFrame([{"Item": a, "R$/ano": b, "R$/boi": b / cv if cv else 0,
                              "% da receita": b / r["receita"] if r["receita"] else 0} for a, b in dre])

    fl = r["fluxos"]
    t["Fluxo de caixa"] = pd.DataFrame({"Ano": range(len(fl)), "Fluxo líquido": fl, "Acumulado": np.cumsum(fl),
                                        "Fluxo descontado": r["fluxos_desc"], "Descontado acumulado": np.cumsum(r["fluxos_desc"])})

    prem = [("Bois por ciclo", num(p["cab"])), ("Ciclos por ano", num(p["ciclos"])), ("Dias de cocho", num(p["dias"])),
            ("Dias de operação no ano", num(p["dias_ano"])), ("Capacidade estática", f"{num(capacidade_total(pj))} vagas"),
            ("Peso de entrada", f"{num(p['pe'], 1)} kg"), ("GMD", f"{num(p['gmd'], 2)} kg/dia"),
            ("Peso de saída", f"{num(r['ps'], 1)} kg"), ("Rendimento de carcaça", pct(p["rc"], 2)),
            ("@ de carcaça por boi", num(r["arr_sai"], 2)), ("@ produzidas por boi", num(r["arr_prod"], 2)),
            ("Mortalidade", pct(p["mort"], 2)), ("Consumo de MS", f"{pct(p['cms'], 2)} do PV ({num(r['cms_kg'], 2)} kg/dia)"),
            ("Valor de compra do boi magro", brl(p["vcompra"], 2)), ("Frete + outros de aquisição", brl(p["frete"] + p["outros_aq"], 2)),
            ("Custo pré-confinamento a pasto", brl(p["pasto"], 2)), ("Preço de venda", f"{brl(p['pvenda'], 2)}/@"),
            ("Funrural + Senar", pct(p["funrural"], 2)), ("TMA", pct(p["tma"], 2)),
            ("Custo da dieta", f"{brl(r['custo_kg_ms'], 3)}/kg MS")]
    t["Premissas"] = pd.DataFrame(prem, columns=["Premissa", "Valor"])

    t["Dieta"] = pd.DataFrame([{"Ingrediente": i["ingrediente"], "MS (%)": _f(i["ms"]) * 100,
                                "Inclusão (% MS)": _f(i["inclusao"]) * 100, "Preço (R$/t MN)": _f(i["preco_t"]),
                                "Custo na dieta (R$/t MS)": _f(i["inclusao"]) * _f(i["preco_t"]) / _f(i["ms"]) if _f(i["ms"]) else 0}
                               for i in pj["dieta"]])
    t["Custos operacionais"] = pd.DataFrame([{"Item": l["item"], "Grupo": l["grupo"], "Classe": l["classe"],
                                              "Base": BASES.get(l["base"], l["base"]), "Rateio (%)": _f(l.get("rateio"), 1) * 100,
                                              "Custo no ano": l["anual"]} for l in valor_anual_custos(pj)])
    rc = resumo_combustivel(pj)
    t["Combustível"] = pd.DataFrame([{"Máquina": m["maquina"], "Potência (cv)": m["cv"], "L/h": m["l_h"],
                                      "Horas/dia": m["horas_dia"], "Litros/ano": m["litros_ano"]} for m in rc["maquinas"]] +
                                    [{"Máquina": "Veículo de apoio (gasolina)", "Litros/ano": rc["litros_gasolina"]}])
    ri = resumo_investimento(pj["investimento"])
    t["Investimento"] = pd.DataFrame([{"Item": l["item"], "Qtd": l["quantidade"], "Valor unit.": l["valor_unit"],
                                       "% uso": _f(l.get("uso"), 1) * 100, "Valor atribuído": l["valor_atribuido"],
                                       "Vida útil": l["vida"], "Depreciação/ano": l["depreciacao"]} for l in ri["linhas"]])
    t["Currais"] = pd.DataFrame([{"Curral": cu.get("curral"), "Linha": cu.get("linha"), "Capacidade": cu.get("capacidade"),
                                  "Área (ha)": cu.get("area_ha"), "Animais": cu.get("animais"), "Dias de cocho": cu.get("dias_cocho"),
                                  "GMD": cu.get("gmd"), "Custo/boi": cu.get("custo_cab"), "Mortes": cu.get("mortes")}
                                 for cu in pj["currais"]])
    return t


MOEDA = {"R$/ano", "R$/boi", "R$/@ vendida", "Fluxo líquido", "Acumulado", "Fluxo descontado", "Descontado acumulado",
         "Custo no ano", "Valor unit.", "Valor atribuído", "Depreciação/ano", "Preço (R$/t MN)", "Custo na dieta (R$/t MS)",
         "Custo/boi"}
PERC = {"% do CT", "% da receita"}


def excel_bytes(c, tabs) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        capa = pd.DataFrame([("Projeto", ui.nome_fazenda(c.pj)), ("Gerado em", dt.date.today().strftime("%d/%m/%Y")),
                             ("Ferramenta", "ConfinaCusto — Custos nos Agronegócios (UnB)")], columns=["", " "])
        capa.to_excel(xw, sheet_name="Capa", index=False)
        for nome, df in tabs.items():
            df.to_excel(xw, sheet_name=nome[:31], index=False)
            ws = xw.sheets[nome[:31]]
            for j, col in enumerate(df.columns, start=1):
                letra = ws.cell(row=1, column=j).column_letter
                ws.column_dimensions[letra].width = max(12, min(48, int(df[col].astype(str).str.len().max() if len(df) else 10) + 4,
                                                                len(str(col)) + 4))
                fmt = 'R$ #,##0;(R$ #,##0);"-"' if col in MOEDA else ("0.0%" if col in PERC else None)
                if fmt:
                    for i in range(2, len(df) + 2):
                        ws.cell(row=i, column=j).number_format = fmt
    return buf.getvalue()


def _fmt_celula(col, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if col in MOEDA:
        return brl(v)
    if col in PERC:
        return pct(v)
    if isinstance(v, (int, float, np.number)):
        return num(v, 2 if abs(v) < 100 and v != int(v) else 0)
    return html.escape(str(v))


def html_relatorio(c, tabs, secoes) -> str:
    r = c.r
    f = c.pj["fazenda"]
    kpis = [("Resultado por boi", brl(r["res_op_cab"])), ("Custo da @ produzida", brl(r["cprod_coe"], 2)),
            ("Equilíbrio (CT)", f"{brl(r['pe_ct'], 2)}/@"), ("VPL", brl(r["vpl"])), ("TIR", pct(r["tir"])),
            ("Payback", f"{num(r['payback'], 1)} anos" if r["payback"] else "> 10 anos")]
    corpo = ""
    for nome in secoes:
        df = tabs[nome]
        if df.empty:
            continue
        th = "".join(f"<th>{html.escape(str(cn))}</th>" for cn in df.columns)
        trs = ""
        for _, row in df.iterrows():
            primeira = str(row.iloc[0])
            cls = ' class="tot"' if primeira.startswith("(=)") else ""
            trs += f"<tr{cls}>" + "".join(f"<td>{_fmt_celula(cn, row[cn])}</td>" for cn in df.columns) + "</tr>"
        corpo += f"<h2>{html.escape(nome)}</h2><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"
    local = ", ".join(x for x in (f.get("municipio"), f.get("uf")) if x)
    sub = " · ".join(x for x in (local, f.get("sistema", ""), f.get("ciclo", ""),
                                 f"gerado em {dt.date.today().strftime('%d/%m/%Y')}") if x)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório — {html.escape(ui.nome_fazenda(c.pj))}</title>
<style>
 body {{font-family: 'Segoe UI', Arial, sans-serif; color:#1C2B24; margin:32px auto; max-width:960px; font-size:13px;}}
 header {{border-bottom:3px solid #1F6B4A; padding-bottom:10px; margin-bottom:18px;}}
 h1 {{font-size:22px; margin:0;}} .sub {{color:#5D6B64; margin-top:4px;}}
 h2 {{font-size:15px; color:#1F6B4A; margin:26px 0 8px; border-bottom:1px solid #DCE4DF; padding-bottom:4px;}}
 .kpis {{display:grid; grid-template-columns:repeat(3,1fr); gap:10px;}}
 .kpi {{border:1px solid #DCE4DF; border-radius:6px; padding:10px 12px;}}
 .kpi b {{display:block; font-size:18px; margin-top:2px;}} .kpi span {{color:#5D6B64; font-size:12px;}}
 table {{width:100%; border-collapse:collapse;}}
 th {{text-align:left; background:#14342A; color:#fff; padding:6px 8px; font-weight:600; font-size:12px;}}
 td {{padding:5px 8px; border-bottom:1px solid #EEF2EF;}} td:not(:first-child) {{text-align:right;}}
 th:not(:first-child) {{text-align:right;}}
 tr.tot td {{font-weight:700; background:#F2F5F3;}}
 footer {{margin-top:30px; color:#7A8780; font-size:11px; border-top:1px solid #DCE4DF; padding-top:8px;}}
 @media print {{ body {{margin:12mm;}} h2 {{break-after:avoid;}} table {{break-inside:auto;}} tr {{break-inside:avoid;}} }}
</style></head><body>
<header><h1>Relatório de custos e viabilidade — {html.escape(ui.nome_fazenda(c.pj))}</h1>
<div class="sub">{html.escape(sub)}</div></header>
<div class="kpis">{''.join(f'<div class="kpi"><span>{a}</span><b>{b}</b></div>' for a, b in kpis)}</div>
{corpo}
<footer>Metodologia: COE (custo operacional efetivo) → COT (+ depreciação) → CT (+ custo de oportunidade do capital),
conforme CONAB/IEA; custeio variável para margem de contribuição e ponto de equilíbrio; rateio de despesas comuns
por critério declarado. Gerado pelo ConfinaCusto — Custos nos Agronegócios, UnB.</footer>
</body></html>"""


def pagina_relatorios():
    st.session_state.last_page = "relatorios"
    c = ui.contexto()
    ui.topo("Emitir", "Relatórios", f"{ui.nome_fazenda(c.pj)} · escolha o que entra, confira a prévia e baixe.",
            "milho")
    ui.exige_calculo(c)
    tabs = tabelas(c)
    padrao = ["Indicadores", "Custo de produção", "DRE", "Fluxo de caixa", "Premissas"]
    topo = ui.card()
    with topo:
        ui.titulo_card("Seções do relatório", "toque para incluir ou tirar")
    secoes = topo.pills("Seções do relatório", list(tabs), default=padrao, selection_mode="multi",
                        label_visibility="collapsed")
    secoes = [s for s in tabs if s in (secoes or [])]

    b = topo.columns([1, 1, 2])
    b[0].download_button("Baixar em Excel", excel_bytes(c, {k: tabs[k] for k in secoes}),
                         file_name=f"relatorio_{dt.date.today():%Y%m%d}.xlsx", icon=":material/table_view:",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
                         disabled=not secoes)
    b[1].download_button("Baixar para imprimir", html_relatorio(c, tabs, secoes).encode("utf-8"),
                         file_name=f"relatorio_{dt.date.today():%Y%m%d}.html", icon=":material/print:",
                         mime="text/html", width="stretch", disabled=not secoes)
    b[2].caption("A versão para imprimir abre no navegador: use Ctrl + P → 'Salvar como PDF'.")

    if not secoes:
        st.info("Escolha pelo menos uma seção.")
        return
    st.write("")
    abas = ui.card().tabs(secoes)
    for aba, nome in zip(abas, secoes):
        with aba:
            df = tabs[nome]
            cfg = {col: st.column_config.NumberColumn(format="R$ %.0f") for col in df.columns if col in MOEDA}
            cfg.update({col: st.column_config.NumberColumn(format="percent") for col in df.columns if col in PERC})
            st.dataframe(df, hide_index=True, column_config=cfg, height=min(36 * (len(df) + 1) + 4, 720))
