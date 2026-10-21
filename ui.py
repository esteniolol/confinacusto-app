"""Estilo, formatação e estado compartilhado entre as telas."""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import streamlit as st

from engine import base_de_projeto, calcular, pode_calcular, validar
from projeto_io import achar_arquivo, projeto_exemplo

VERDE, VERDE_ESC, VERDE_CLARO = "#3F5D57", "#2C443F", "#DCEAE6"
AMBAR, VERMELHO, CINZA = "#D9A62E", "#D9785F", "#B7C4C0"
TEAL, AZUL, FUNDO = "#2BB3A3", "#2A8FBD", "#E6EFEC"
FONTE = "Poppins, Source Sans Pro, sans-serif"

# Benchmark Confina Brasil 2025 (Scot Consultoria) — diária R$/cab/dia
BENCH = {"Goiás": 15.61, "São Paulo": 16.45, "Mato Grosso do Sul": 14.85, "Minas Gerais": 14.70,
         "Média Brasil": 14.78, "Mato Grosso": 13.03}

PAGINAS: dict = {}   # preenchido no app.py (para links entre telas)
DIR_ILU = Path(__file__).parent / "dados" / "ilustracoes"

_ONDAS = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 130' "
          "preserveAspectRatio='none'><g fill='none' stroke='white' stroke-opacity='.2' stroke-width='1.3'>"
          "<path d='M95 0 C130 46 170 6 210 44 S280 70 300 34'/><path d='M120 0 C150 34 196 12 236 52 S290 84 300 70'/>"
          "<path d='M60 130 C110 96 160 120 210 98 S270 84 300 104'/></g></svg>")

CSS = """
<style>
:root{
  --oc-bg:#E6EFEC; --oc-side:#3F5D57; --oc-side2:#4A6A63; --oc-gold:#D9A62E; --oc-gold2:#B9861A;
  --oc-ink:#23332F; --oc-mute:#70827C; --oc-card:#FFFFFF; --oc-line:#E4ECE9; --oc-teal:#2BB3A3;
  --oc-sombra:0 1px 2px rgba(35,51,47,.05), 0 12px 30px -14px rgba(35,51,47,.22);
  --oc-ease:cubic-bezier(.22,.8,.24,1);
}
@property --p {syntax:'<number>'; inherits:false; initial-value:0;}

/* ---------- fundo ---------- */
.stApp{background:var(--oc-bg);}
.stApp::before{content:"";position:fixed;left:-150px;top:-170px;width:430px;height:430px;border-radius:50%;
  background:var(--oc-gold);z-index:0;pointer-events:none;}
.stApp::after{content:"";position:fixed;right:-240px;bottom:-280px;width:660px;height:660px;border-radius:50%;
  background:#D5E5E0;z-index:0;pointer-events:none;}
[data-testid="stMain"]{position:relative;z-index:1;background:transparent;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.5rem;padding-bottom:3rem;max-width:1380px;}

/* ---------- barra lateral (cartão arredondado) ---------- */
section[data-testid="stSidebar"]{background:transparent !important;border-right:0 !important;box-shadow:none !important;}
@media (min-width: 769px){section[data-testid="stSidebar"][data-collapsed="false"]{width:292px !important;min-width:292px !important;}}
[data-testid="stSidebarContent"]{background:var(--oc-side) !important;margin:14px 0 14px 14px;border-radius:30px;
  width:calc(100% - 14px) !important;padding:0 !important;
  height:calc(100% - 28px);box-shadow:0 22px 44px -22px rgba(20,40,35,.65);overflow-x:hidden;}
[data-testid="stSidebarHeader"]{padding:.7rem 1rem 0 1.2rem;height:auto;min-height:0;}
[data-testid="stSidebarUserContent"]{padding:0 1.35rem 1.2rem 1.35rem !important;margin:0 !important;}
[data-testid="stSidebarCollapseButton"] span{color:#CFE0DA !important;}

.oc-marca{display:flex;align-items:center;gap:.45rem;color:#fff;font-weight:700;font-size:1rem;letter-spacing:.01em;}
.oc-marca span{color:var(--oc-gold);}
.oc-perfil{text-align:center;padding:.3rem 0 1rem 0;margin-bottom:.2rem;}
.oc-avatar{width:98px;height:98px;margin:0 auto .65rem;border-radius:50%;padding:5px;
  background:conic-gradient(var(--oc-gold) calc(var(--p) * 1%), rgba(255,255,255,.13) 0);
  animation:ocAnel 1.4s var(--oc-ease) both;}
.oc-avatar > div{width:100%;height:100%;border-radius:50%;background:#F7F2E6;border:4px solid var(--oc-side);
  display:flex;align-items:flex-end;justify-content:center;overflow:hidden;}
.oc-avatar img{width:92%;margin-bottom:-6%;transition:transform .5s var(--oc-ease);}
.oc-avatar:hover img{transform:translateY(-6px) rotate(-4deg);}
.oc-nome{color:#fff;font-weight:600;letter-spacing:.06em;text-transform:uppercase;font-size:.95rem;line-height:1.25;}
.oc-sub{color:#B7CBC4;font-size:.76rem;margin-top:.15rem;}
.oc-prog{color:#B7CBC4;font-size:.72rem;margin-top:.45rem;}
.oc-prog b{color:var(--oc-gold);}
.oc-secao{color:var(--oc-gold);font-size:.66rem;letter-spacing:.16em;font-weight:600;text-transform:uppercase;
  margin:1rem 0 .95rem 1rem;}

[class*="st-key-navbox"]{gap:.12rem !important;}
[class*="st-key-nav-"]{gap:0 !important;}
[class*="st-key-nav-"] a{border-radius:999px 0 0 999px;padding:.58rem 1rem .58rem 1rem;width:calc(100% + 1.35rem) !important;
  max-width:none !important;
  position:relative;background:transparent;transition:transform .3s var(--oc-ease), background-color .3s;}
[class*="st-key-nav-"] a p{color:#E6EFEB !important;text-transform:uppercase;letter-spacing:.07em;font-size:.8rem;
  font-weight:500;transition:color .3s;}
[class*="st-key-nav-"] a [data-testid="stIconMaterial"]{color:var(--oc-gold) !important;transition:transform .35s var(--oc-ease);}
[class*="st-key-nav-off"] a:hover{background:rgba(255,255,255,.07);transform:translateX(5px);}
[class*="st-key-nav-off"] a:hover [data-testid="stIconMaterial"]{transform:scale(1.15) rotate(-6deg);}
[class*="st-key-nav-on"] a{background:linear-gradient(var(--oc-bg),var(--oc-bg)) no-repeat right center / 100% 100%;
  animation:ocPuxa .55s var(--oc-ease) both;}
[class*="st-key-nav-on"] a p{color:var(--oc-side) !important;font-weight:600;animation:ocTexto .55s var(--oc-ease) both;}
[class*="st-key-nav-on"] a::before,[class*="st-key-nav-on"] a::after{content:"";position:absolute;right:0;width:22px;
  height:22px;pointer-events:none;animation:ocAparece .3s .3s both;}
[class*="st-key-nav-on"] a::before{top:-22px;background:radial-gradient(circle at 0 0, transparent 21.5px, var(--oc-bg) 22px);}
[class*="st-key-nav-on"] a::after{bottom:-22px;background:radial-gradient(circle at 0 100%, transparent 21.5px, var(--oc-bg) 22px);}

[data-testid="stSidebar"] [data-testid="stDownloadButton"] button{background:var(--oc-gold);border:0;border-radius:999px;
  transition:transform .25s var(--oc-ease), box-shadow .25s;}
[data-testid="stSidebar"] [data-testid="stDownloadButton"] button p{color:#2A230F !important;font-weight:600;}
[data-testid="stSidebar"] [data-testid="stDownloadButton"] button span{color:#2A230F !important;}
[data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover{transform:translateY(-2px);
  box-shadow:0 10px 20px -10px rgba(0,0,0,.6);}
.oc-rodape{position:relative;margin-top:.6rem;padding-top:.4rem;text-align:center;}
.oc-rodape .cena{position:relative;height:84px;}
.oc-rodape .cena img{position:absolute;bottom:0;}
.oc-rodape .cena .b{left:4px;height:78px;animation:ocPasta 6s ease-in-out infinite;transform-origin:bottom center;}
.oc-rodape .cena .m{right:8px;height:72px;animation:ocBalanca 5s ease-in-out infinite;transform-origin:bottom center;}
.oc-rodape .chao{height:6px;border-radius:6px;background:rgba(255,255,255,.08);margin-top:-2px;}
.oc-rodape p{color:#9FB7AF;font-size:.7rem;margin:.6rem 0 0;line-height:1.4;}

/* ---------- cabeçalho das telas ---------- */
.oc-topo{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:0 0 .6rem 0;}
.oc-kicker{font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;color:var(--oc-gold2);font-weight:600;}
.oc-titulo{font-size:1.75rem;font-weight:700;color:var(--oc-ink);line-height:1.15;margin:.15rem 0 .25rem;letter-spacing:-.01em;}
.oc-subt{color:var(--oc-mute);font-size:.9rem;}
.oc-topo img{height:84px;animation:ocFlutua 5s ease-in-out infinite;filter:drop-shadow(0 8px 8px rgba(35,51,47,.12));}

/* ---------- cartões ---------- */
[class*="st-key-card"]{background:var(--oc-card);border:0 !important;border-radius:24px !important;
  box-shadow:var(--oc-sombra);padding:1.15rem 1.3rem !important;
  transition:transform .4s var(--oc-ease), box-shadow .4s var(--oc-ease);}
[class*="st-key-cardh"]:hover{transform:translateY(-4px);
  box-shadow:0 2px 4px rgba(35,51,47,.05),0 22px 40px -16px rgba(35,51,47,.32);}
[data-testid="stMetric"]{background:#fff;border:0 !important;border-radius:20px !important;box-shadow:var(--oc-sombra);
  padding:.95rem 1.1rem !important;transition:transform .35s var(--oc-ease);}
[data-testid="stMetric"]:hover{transform:translateY(-3px);}
[class*="st-key-card"] [data-testid="stMetric"]{box-shadow:none;background:#F3F7F5;padding:.75rem .9rem !important;}
[class*="st-key-card"] [data-testid="stMetricValue"]{font-size:1.2rem;}
[data-testid="stMetricLabel"] p{font-size:.76rem;color:var(--oc-mute);}
[data-testid="stMetricDelta"]{font-size:.74rem;}
[data-testid="stMetricValue"]{font-size:1.4rem;color:var(--oc-ink);}
.oc-card-tit{font-weight:600;font-size:1.02rem;color:var(--oc-ink);margin:0;}
.oc-card-sub{color:var(--oc-mute);font-size:.76rem;margin:.05rem 0 .3rem;}
.oc-ilu-card{display:flex;justify-content:center;align-items:flex-end;height:84px;margin:.1rem 0 .5rem;}
.oc-ilu-card img{max-height:84px;max-width:80%;transition:transform .5s var(--oc-ease);}
[class*="st-key-cardh"]:hover .oc-ilu-card img{transform:translateY(-6px) scale(1.06) rotate(-3deg);}

/* ---------- cartões de destaque ---------- */
.oc-hero{position:relative;border-radius:24px;padding:1.05rem 1.3rem;height:138px;color:#fff;
  box-shadow:0 16px 30px -18px rgba(30,50,45,.7);transition:transform .4s var(--oc-ease);isolation:isolate;}
.oc-hero::before{content:"";position:absolute;inset:0;border-radius:inherit;z-index:-1;
  background:url("ONDAS") no-repeat center/100% 100%;}
.oc-hero:hover{transform:translateY(-4px);}
.oc-hero.ouro{background:linear-gradient(135deg,#E3B445 0%,#CC9624 100%);}
.oc-hero.escuro{background:linear-gradient(135deg,#4A6B64 0%,#36524C 100%);}
.oc-hero.teal{background:linear-gradient(135deg,#36BFAE 0%,#22988A 100%);}
.oc-hero .rot{font-size:.84rem;opacity:.95;font-weight:500;}
.oc-hero .val{font-size:1.8rem;font-weight:700;margin-top:.1rem;letter-spacing:-.01em;line-height:1.2;}
.oc-hero .sub{font-size:.74rem;opacity:.88;margin-top:.25rem;max-width:58%;line-height:1.35;}
.oc-hero img{position:absolute;right:8px;bottom:-10px;height:104px;filter:drop-shadow(0 10px 10px rgba(0,0,0,.2));
  animation:ocFlutua 4.5s ease-in-out infinite;}
.oc-hero:hover img{animation-duration:1.6s;}
.oc-hero .pontos{position:absolute;right:16px;top:16px;bottom:16px;width:36%;display:grid;
  grid-template-columns:repeat(var(--cols),1fr);gap:4px;align-content:center;}
.oc-hero .pontos i{display:block;aspect-ratio:1;border-radius:4px;background:rgba(255,255,255,.18);
  animation:ocPop .5s var(--oc-ease) both;}
.oc-hero .pontos i.on{background:var(--oc-gold);}

.oc-boas{position:relative;border-radius:28px;padding:1.6rem 1.8rem;min-height:190px;color:#fff;overflow:hidden;
  background:linear-gradient(120deg,#3F5D57 0%,#4D7068 60%,#5B7F76 100%);box-shadow:0 22px 40px -24px rgba(25,45,40,.8);}
.oc-boas::before{content:"";position:absolute;right:-60px;top:-80px;width:300px;height:300px;border-radius:50%;
  background:rgba(217,166,46,.9);}
.oc-boas .k{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:#F1D27F;font-weight:600;}
.oc-boas h2{color:#fff;font-size:1.9rem;font-weight:700;margin:.2rem 0 .3rem;padding:0;line-height:1.15;}
.oc-boas p{color:#D6E4DF;font-size:.9rem;max-width:52%;margin:0;}
.oc-boas .chips{margin-top:.8rem;max-width:56%;}
.oc-boas .chips span{display:inline-block;background:rgba(255,255,255,.12);color:#fff;border-radius:999px;
  padding:.18rem .7rem;font-size:.75rem;margin:0 .35rem .35rem 0;}
.oc-boas img{position:absolute;bottom:-4px;}
.oc-boas .v{right:150px;height:176px;animation:ocEspia 6s ease-in-out infinite;transform-origin:bottom center;}
.oc-boas .m{right:40px;height:132px;animation:ocBalanca 5s ease-in-out infinite;transform-origin:bottom center;}
.oc-boas .t{right:300px;height:78px;bottom:6px;opacity:.95;animation:ocAnda 9s ease-in-out infinite;}

/* ---------- elementos ---------- */
.tag{display:inline-block;padding:.12rem .62rem;border-radius:999px;font-size:.74rem;background:#E3EFEA;color:#3F5D57;
  margin:0 .35rem .3rem 0;border:1px solid #D2E3DC;}
.tag.warn{background:#FBF1DC;color:#8A5F10;border-color:#F0DDB0;}
.tag.off{background:#F1F4F3;color:#7A8780;border-color:#E1E6E3;}
.nota{font-size:.76rem;color:var(--oc-mute);}
.insight{border-left:4px solid var(--oc-gold);background:#FBF6EA;padding:.65rem .95rem;border-radius:0 14px 14px 0;
  font-size:.88rem;margin:.3rem 0 .6rem 0;}
.passo-titulo{font-size:.7rem;text-transform:uppercase;letter-spacing:.14em;color:var(--oc-gold2);font-weight:600;}
.vivo{font-size:.72rem;color:#2BA594;font-weight:600;letter-spacing:.08em;}
.vivo::first-letter{animation:ocPulsa 1.6s ease-in-out infinite;}
.oc-passo{display:flex;align-items:center;justify-content:space-between;gap:1rem;}
.oc-passo img{height:74px;animation:ocFlutua 5s ease-in-out infinite;}
.oc-vazio{display:flex;align-items:center;gap:1.2rem;background:#fff;border-radius:24px;padding:1rem 1.4rem;
  box-shadow:var(--oc-sombra);margin:.4rem 0 1rem;}
.oc-vazio img{height:96px;animation:ocEspia 5s ease-in-out infinite;transform-origin:bottom center;}
.oc-vazio b{font-size:1.02rem;}

[data-testid="stBaseButton-primary"]{box-shadow:0 10px 18px -12px rgba(63,93,87,.9);transition:transform .25s var(--oc-ease);}
[data-testid="stBaseButton-primary"]:hover{transform:translateY(-2px);}
[data-testid="stTabs"] [role="tablist"]{gap:.35rem;border:0 !important;box-shadow:none !important;flex-wrap:wrap;}
[data-testid="stTab"]{border-radius:999px;padding:.32rem 1rem !important;transition:background-color .35s, color .35s;}
[data-testid="stTab"]:hover{background:#EEF4F1;}
[data-testid="stTab"] > div:not([data-testid]){display:none !important;}
[data-testid="stTab"][data-selected="true"]{background:var(--oc-side);}
[data-testid="stTab"][data-selected="true"] p{color:#fff !important;}
[data-testid="stTabs"] [role="tabpanel"]{animation:ocSobe .45s var(--oc-ease) both;}
[data-testid="stButtonGroup"] [role="toolbar"]{gap:.4rem;flex-wrap:wrap;}
[data-testid="stButtonGroup"] button[data-variant]{border-radius:999px !important;background:#F2F7F5;border:1px solid #DCE7E3 !important;
  transition:background-color .3s, color .3s, transform .25s var(--oc-ease), box-shadow .3s;}
[data-testid="stButtonGroup"] button[data-variant]:hover{transform:translateY(-2px);box-shadow:0 8px 14px -10px rgba(35,51,47,.5);}
[data-testid="stButtonGroup"] button[data-variant][data-selected="true"]{background:var(--oc-side) !important;
  border-color:var(--oc-side) !important;box-shadow:0 8px 16px -10px rgba(63,93,87,.9);}
[data-testid="stButtonGroup"] button[data-variant][data-selected="true"] p{color:#fff !important;}
[data-testid="stPageLink"] a{transition:transform .25s var(--oc-ease);}
[data-testid="stPageLink"] a:hover{transform:translateX(3px);}

/* ---------- transições entre telas ---------- */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > *{animation:ocSobe .6s var(--oc-ease) both;}
""" + "".join(f'[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > *:nth-child({i})'
              f'{{animation-delay:{0.04 * (i - 1):.2f}s;}}\n' for i in range(2, 16)) + """
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{animation:ocSobe .6s var(--oc-ease) both;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2){animation-delay:.06s;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3){animation-delay:.12s;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4){animation-delay:.18s;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(5){animation-delay:.24s;}

@keyframes ocSobe{from{opacity:0;transform:translateY(18px);}to{opacity:1;transform:none;}}
@keyframes ocFlutua{0%,100%{transform:translateY(0);}50%{transform:translateY(-6px);}}
@keyframes ocPuxa{from{background-size:0% 100%;}to{background-size:100% 100%;}}
@keyframes ocTexto{from{color:#E6EFEB;}to{color:var(--oc-side);}}
@keyframes ocAparece{from{opacity:0;}to{opacity:1;}}
@keyframes ocAnel{from{--p:0;}}
@keyframes ocPop{from{opacity:0;transform:scale(.3);}to{opacity:1;transform:none;}}
@keyframes ocPulsa{0%,100%{opacity:1;}50%{opacity:.25;}}
@keyframes ocBalanca{0%,100%{transform:rotate(-3deg);}50%{transform:rotate(3deg);}}
@keyframes ocPasta{0%,100%{transform:rotate(0);}40%{transform:rotate(-2deg) translateX(2px);}60%{transform:rotate(1deg);}}
@keyframes ocEspia{0%,70%,100%{transform:translateY(0) rotate(0);}78%{transform:translateY(-8px) rotate(-3deg);}
  86%{transform:translateY(-4px) rotate(3deg);}}
@keyframes ocAnda{0%,100%{transform:translateX(0);}50%{transform:translateX(-26px);}}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none !important;transition:none !important;}}
@media (max-width: 900px){.oc-boas p,.oc-boas .chips{max-width:100%;} .oc-boas img{display:none;}
  .oc-hero .sub{max-width:100%;} .oc-topo img{display:none;}}


/* ---------- tela de entrada ---------- */
.stMainBlockContainer:has(.st-key-gate){max-width:1140px !important;padding-top:2.6rem !important;}
.gate-marca{display:flex;align-items:center;gap:.6rem;font-weight:700;font-size:1.25rem;color:var(--oc-ink);}
.gate-marca span{color:var(--oc-gold2);} .gate-marca img{height:34px;}
.gate-k{margin-top:2rem;}
.gate-h1{font-size:2.5rem;font-weight:700;line-height:1.12;letter-spacing:-.01em;color:var(--oc-ink);margin:.3rem 0 .4rem;}
.gate-sub{color:var(--oc-mute);font-size:1rem;max-width:640px;margin-bottom:1rem;}
.st-key-gate-ouro,.st-key-gate-verde{position:relative;border-radius:30px;padding:1.9rem 2rem 1.8rem !important;
  min-height:400px;overflow:hidden;box-shadow:0 26px 50px -26px rgba(25,45,40,.8);
  transition:transform .45s var(--oc-ease), box-shadow .45s var(--oc-ease);}
.st-key-gate-ouro{background:linear-gradient(140deg,#E3B445,#C8901F);}
.st-key-gate-verde{background:linear-gradient(140deg,#4D6E66,#34504A);}
.st-key-gate-ouro:hover,.st-key-gate-verde:hover{transform:translateY(-6px);box-shadow:0 34px 60px -28px rgba(25,45,40,.9);}
.st-key-gate-ouro::after,.st-key-gate-verde::after{content:"";position:absolute;right:-90px;top:-110px;width:280px;
  height:280px;border-radius:50%;background:rgba(255,255,255,.12);pointer-events:none;}
.gate-txt{position:relative;z-index:2;max-width:56%;color:#fff;}
.st-key-gate-ouro [data-testid="stElementContainer"],.st-key-gate-ouro [data-testid="stMarkdown"],
.st-key-gate-ouro [data-testid="stMarkdownContainer"],.st-key-gate-verde [data-testid="stElementContainer"],
.st-key-gate-verde [data-testid="stMarkdown"],.st-key-gate-verde [data-testid="stMarkdownContainer"]{position:static !important;}
.gate-tag{display:inline-block;background:rgba(255,255,255,.22);border-radius:999px;padding:.2rem .75rem;font-size:.72rem;
  font-weight:600;letter-spacing:.05em;color:#fff;}
.gate-h2{font-size:1.85rem;font-weight:700;line-height:1.15;margin:.9rem 0 .45rem;color:#fff;}
.gate-txt p{font-size:.9rem;color:rgba(255,255,255,.92);margin:0 0 .8rem;}
.gate-lista{list-style:none;padding:0 !important;margin:0 0 .4rem !important;}
.gate-lista li{font-size:.84rem;color:#fff;margin:.3rem 0 !important;display:flex;gap:.5rem;align-items:center;}
.gate-lista li::before{content:"✓";width:18px;height:18px;border-radius:50%;background:rgba(255,255,255,.25);
  font-size:.65rem;display:inline-flex;align-items:center;justify-content:center;flex:none;}
.gate-ilu{position:absolute;right:22px;bottom:22px;z-index:1;display:flex;align-items:flex-end;gap:4px;pointer-events:none;}
.gate-ilu img{animation:ocFlutua 5s ease-in-out infinite;}
.st-key-gate-ouro .gate-ilu .a{height:108px;} .st-key-gate-ouro .gate-ilu .b{height:92px;animation-delay:.6s;}
.st-key-gate-verde .gate-ilu .a{height:62px;margin-right:-12px;} .st-key-gate-verde .gate-ilu .b{height:136px;animation-delay:.6s;}
.st-key-gate-ouro:hover .gate-ilu img,.st-key-gate-verde:hover .gate-ilu img{animation-duration:1.4s;}
.st-key-gate-ouro button,.st-key-gate-verde button{position:relative;z-index:2;border:0 !important;border-radius:999px !important;
  padding:.8rem 1.6rem !important;min-height:0 !important;box-shadow:0 12px 22px -12px rgba(0,0,0,.6);
  transition:transform .25s var(--oc-ease);}
.st-key-gate-ouro button:hover,.st-key-gate-verde button:hover{transform:translateX(4px);}
.st-key-gate-ouro button{background:#23332F !important;} .st-key-gate-ouro button p{color:#fff !important;font-weight:600;font-size:.95rem;}
.st-key-gate-verde button{background:var(--oc-gold) !important;} .st-key-gate-verde button p{color:#2A230F !important;font-weight:600;font-size:.95rem;}
.st-key-gate-links{flex-direction:row !important;justify-content:center;flex-wrap:wrap;gap:.8rem !important;margin-top:.6rem;}
.st-key-gate-links > div{width:auto !important;flex:0 0 auto;}
.st-key-gate-links [data-testid="stPopover"] button{background:#fff;border:0;border-radius:999px;padding:.55rem 1.2rem;
  box-shadow:0 10px 20px -16px rgba(35,51,47,.6);}
.st-key-gate-links [data-testid="stPopover"] button p{color:var(--oc-side);font-weight:500;}
.st-key-gate-links [data-testid="stPopover"] button [data-testid="stIconMaterial"]{color:var(--oc-gold2);}
.gate-nota{text-align:center;color:#7B8C86;font-size:.75rem;margin-top:.4rem;}
@media (max-width: 768px){
  .stMainBlockContainer:has(.st-key-gate){padding:1.6rem 1rem 2rem !important;}
  .gate-k{margin-top:1.4rem;} .gate-h1{font-size:1.8rem;} .gate-sub{font-size:.9rem;}
  .st-key-gate-ouro,.st-key-gate-verde{min-height:0;padding:1.4rem 1.4rem 1.4rem !important;border-radius:24px;}
  .gate-txt{max-width:100%;} .gate-h2{font-size:1.45rem;max-width:62%;} .gate-txt p{max-width:62%;font-size:.84rem;}
  .gate-lista{display:none;}
  .gate-ilu{top:18px;bottom:auto;right:14px;}
  .st-key-gate-ouro .gate-ilu .a{height:66px;} .st-key-gate-ouro .gate-ilu .b{display:none;}
  .st-key-gate-verde .gate-ilu .a{display:none;} .st-key-gate-verde .gate-ilu .b{height:96px;}
  .st-key-gate-ouro button,.st-key-gate-verde button{width:100% !important;}
  .st-key-gate-links{flex-direction:column !important;}
  .st-key-gate-links > div{width:100% !important;}
  .st-key-gate-links [data-testid="stPopover"] button{width:100%;justify-content:center;}
}

/* ---------- barra de navegação do celular (escondida no computador) ---------- */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > *:has(.st-key-mobnav),
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > *:has(.st-key-vivomob){animation:none !important;
  transform:none !important;}
.st-key-mobnav, .st-key-vivomob{display:none !important;}

/* ---------- celular ---------- */
@media (max-width: 768px){
  .stApp::before{width:220px;height:220px;left:-110px;top:-120px;}
  .stApp::after{width:360px;height:360px;right:-200px;bottom:-200px;}
  .block-container{padding:3.4rem .9rem 6.5rem .9rem !important;}
  /* menu lateral por cima do conteúdo */
  section[data-testid="stSidebar"]{position:fixed !important;left:0;top:0;bottom:0;height:100dvh !important;
    width:min(86vw, 320px) !important;min-width:0 !important;z-index:1000002 !important;}
  section[data-testid="stSidebar"][data-collapsed="true"]{transform:translateX(-110%) !important;}
  section[data-testid="stSidebar"][data-collapsed="false"]{transform:none !important;
    box-shadow:0 0 0 100vmax rgba(20,35,32,.45) !important;}
  [data-testid="stSidebarContent"]{margin:10px 0 10px 10px;width:calc(100% - 10px) !important;height:calc(100% - 20px);}
  [data-testid="stExpandSidebarButton"]{background:var(--oc-side) !important;border-radius:999px !important;
    box-shadow:0 8px 18px -8px rgba(20,40,35,.7);}
  [data-testid="stExpandSidebarButton"] span{color:#fff !important;}
  header[data-testid="stHeader"]{background:linear-gradient(var(--oc-bg) 60%, rgba(230,239,236,0)) !important;}
  /* títulos e cartões mais compactos */
  .oc-titulo{font-size:1.4rem;}
  .oc-boas{padding:1.2rem 1.2rem;min-height:0;border-radius:22px;}
  .oc-boas::before{width:180px;height:180px;right:-70px;top:-90px;}
  .oc-boas h2{font-size:1.45rem;}
  .oc-hero{height:118px;border-radius:20px;padding:.9rem 1.1rem;}
  .oc-hero .val{font-size:1.55rem;}
  .oc-hero img{height:82px;bottom:-6px;}
  [class*="st-key-card"]{border-radius:20px !important;padding:.9rem .95rem !important;}
  [class*="st-key-cardh"]:hover{transform:none;}
  .oc-passo img{height:56px;}
  .oc-vazio{padding:.8rem 1rem;} .oc-vazio img{height:70px;}
  /* indicadores dois por linha em vez de um embaixo do outro */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stMetric"]){flex-wrap:wrap !important;
    gap:.6rem !important;}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stMetric"]) > [data-testid="stColumn"]{
    flex:1 1 calc(50% - .6rem) !important;min-width:calc(50% - .6rem) !important;width:calc(50% - .6rem) !important;}
  [data-testid="stMetric"]{padding:.75rem .85rem !important;border-radius:16px !important;}
  [data-testid="stMetricValue"]{font-size:1.12rem;}
  /* barra de navegação fixa embaixo */
  .st-key-mobnav{display:flex !important;flex-direction:row !important;position:fixed;left:10px;right:10px;bottom:10px;
    z-index:1000001;background:var(--oc-side);border-radius:22px;padding:6px 4px !important;gap:0 !important;
    box-shadow:0 14px 30px -12px rgba(20,40,35,.75);justify-content:space-around;animation:none !important;}
  .st-key-mobnav > div{flex:1 1 0;min-width:0;width:auto !important;}
  .st-key-mobnav [data-testid="stPageLink"] a{flex-direction:column;gap:1px;padding:5px 2px !important;border-radius:14px;
    justify-content:center;align-items:center;transition:background-color .3s;}
  .st-key-mobnav [data-testid="stPageLink"] a p{font-size:.6rem !important;color:#D7E5E0 !important;white-space:nowrap;
    letter-spacing:.01em;}
  .st-key-mobnav [data-testid="stPageLink"] a [data-testid="stIconMaterial"]{color:var(--oc-gold) !important;font-size:1.3rem;}
  .st-key-mobnav [class*="st-key-mob-on"] a{background:var(--oc-bg) !important;}
  .st-key-mobnav [class*="st-key-mob-on"] a p{color:var(--oc-side) !important;font-weight:600;}
  /* mapa: rola para o lado em vez de encolher os currais */
  .st-key-mapa, .st-key-cascata{overflow-x:auto !important;-webkit-overflow-scrolling:touch;padding-bottom:4px;}
  .st-key-mapa > div{min-width:780px !important;}
  .st-key-cascata > div{min-width:600px !important;}
  .st-key-cascata::before{content:"arraste para o lado →";display:block;font-size:.68rem;color:var(--oc-mute);
    position:sticky;left:0;}
  .st-key-mapa::before{content:"arraste para o lado para ver todos os currais →";display:block;font-size:.68rem;
    color:var(--oc-mute);margin-bottom:2px;position:sticky;left:0;}
  /* resultado ao vivo fixo no topo do cadastro */
  .st-key-vivomob{display:block !important;}
  [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > *:has(.st-key-vivomob){position:sticky;top:2.9rem;
    z-index:50;}
  .oc-vivomob{display:flex;justify-content:space-between;gap:.6rem;background:var(--oc-side);color:#fff;border-radius:16px;
    padding:.55rem .9rem;box-shadow:0 10px 20px -12px rgba(20,40,35,.8);}
  .oc-vivomob div{display:flex;flex-direction:column;line-height:1.2;}
  .oc-vivomob span{font-size:.62rem;color:#BFD3CC;letter-spacing:.04em;}
  .oc-vivomob b{font-size:.98rem;color:#fff;font-weight:700;}
  .oc-vivomob b.ouro{color:#F1D27F;}
}
</style>
""".replace("ONDAS", _ONDAS)


# ----------------------------------------------------------------------------
# Ilustrações e componentes visuais
# ----------------------------------------------------------------------------
@lru_cache(maxsize=None)
def ilu_uri(nome: str) -> str:
    arq = achar_arquivo(f"{nome}.svg")
    if arq is None:
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(arq.read_bytes()).decode()


def ilu(nome: str, cls: str = "", alt: str = "") -> str:
    uri = ilu_uri(nome)
    if not uri:                # desenho não encontrado: não quebra a tela, só não mostra
        return f'<img class="{cls}" alt="" style="display:none">'
    return f'<img src="{uri}" class="{cls}" alt="{alt or nome}">'


_CARDS = [0]


def novo_ciclo():
    """Zera o contador de cartões a cada execução (as chaves ficam estáveis entre as execuções)."""
    _CARDS[0] = 0


def card(hover: bool = False, key_extra: str = "", **kw):
    """Cartão branco arredondado (st.container com chave para o CSS). key_extra força remontar (e animar)."""
    _CARDS[0] += 1
    sufixo = f"_{key_extra}" if key_extra else ""
    return st.container(border=True, key=f"{'cardh' if hover else 'card'}_{_CARDS[0]}{sufixo}", **kw)


def topo(kicker: str, titulo: str, subtitulo: str = "", ilustracao: str | None = None):
    img = ilu(ilustracao) if ilustracao else ""
    sub = f'<div class="oc-subt">{subtitulo}</div>' if subtitulo else ""
    st.markdown(f'<div class="oc-topo"><div><div class="oc-kicker">{kicker}</div><div class="oc-titulo">{titulo}</div>'
                f'{sub}</div>{img}</div>', unsafe_allow_html=True)


def titulo_card(titulo: str, sub: str = ""):
    s = f'<div class="oc-card-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="oc-card-tit">{titulo}</div>{s}', unsafe_allow_html=True)


def hero(rotulo: str, valor: str, sub: str = "", ilustracao: str | None = None, tema: str = "escuro",
         pontos: tuple[int, int, int] | None = None) -> str:
    """Cartão colorido de destaque. pontos=(total, ocupados, colunas) desenha um mini-mapa de currais."""
    extra = ilu(ilustracao) if ilustracao else ""
    if pontos:
        tot, on, cols = pontos
        cel = "".join(f'<i class="{"on" if i < on else ""}" style="animation-delay:{0.02 * i:.2f}s"></i>'
                      for i in range(tot))
        extra = f'<div class="pontos" style="--cols:{cols}">{cel}</div>'
    s = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="oc-hero {tema}"><div class="rot">{rotulo}</div><div class="val">{valor}</div>{s}{extra}</div>')


def vazio(titulo: str, texto: str = "", ilustracao: str = "vaca"):
    st.markdown(f'<div class="oc-vazio">{ilu(ilustracao)}<div><b>{titulo}</b><br>'
                f'<span class="nota">{texto}</span></div></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Formatação pt-BR
# ----------------------------------------------------------------------------
def num(v, dec=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v, dec=0):
    if v is None:
        return "—"
    sinal = "−" if v < 0 else ""
    return f"{sinal}R$ {num(abs(v), dec)}"


def pct(v, dec=1):
    return "—" if v is None else f"{num(v * 100, dec)}%"


def mi(v):
    return f"R$ {num(v / 1e6, 2)} mi"


def md(texto: str, **kw):
    """st.markdown que não confunde 'R$' com fórmula matemática (só para markdown, não HTML)."""
    st.markdown(texto.replace("$", "\\$"), **kw)


def layout(fig, h=360, legenda=False):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONTE, size=12, color="#23332F"), barcornerradius=7,
        hoverlabel=dict(bgcolor="#3F5D57", font=dict(color="#FFFFFF", family=FONTE), bordercolor="#3F5D57"),
        showlegend=legenda, separators=",.", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor="#EEF3F1", zeroline=False, linecolor="#E4ECE9")
    fig.update_yaxes(gridcolor="#EEF3F1", zeroline=False)
    return fig


# ----------------------------------------------------------------------------
# Estado do projeto
# ----------------------------------------------------------------------------
SIM_KEYS = ("s_venda", "s_compra", "s_milho", "s_gmd", "s_dias", "s_mort", "s_cab", "s_tma", "_milho_base_saca")


def iniciar_estado():
    if "projeto" not in st.session_state:
        st.session_state.projeto = projeto_exemplo()
        st.session_state.ver = 0
        st.session_state.passo = 0
        st.session_state.escolheu = False


def carregar_projeto(pj: dict, passo: int = 0):
    """Troca o projeto aberto e zera os widgets que guardavam valores do projeto anterior."""
    st.session_state.projeto = pj
    st.session_state.ver = st.session_state.get("ver", 0) + 1
    st.session_state.passo = passo
    for k in SIM_KEYS + ("curral_sel",):
        st.session_state.pop(k, None)


def contexto():
    pj = st.session_state.projeto
    pend = validar(pj)
    ok = pode_calcular(pend)
    base = base_de_projeto(pj) if ok else None
    r = calcular(base) if ok else None
    return SimpleNamespace(pj=pj, pend=pend, ok=ok, base=base, r=r)


def exige_calculo(c):
    if not c.ok:
        vazio("O cadastro ainda está incompleto", "Ainda não dá para calcular os resultados. Falta preencher:")
        faltas = [f"**{k}:** {' '.join(v)}" for k, v in c.pend.items() if v and k in ("Lote e desempenho",
                                                                                        "Compra e venda", "Dieta")]
        md("\n".join(f"- {f}" for f in faltas))
        if "cadastro" in PAGINAS:
            st.page_link(PAGINAS["cadastro"], label="Ir para o cadastro", icon=":material/edit_note:")
        st.stop()


def nome_fazenda(pj) -> str:
    return pj["fazenda"].get("nome") or "Projeto sem nome"
