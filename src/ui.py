from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

CORES_COMBUSTIVEL = {
    "Gasolina": "#2a78d6", "Etanol": "#eb6834", "Diesel": "#1baf7a",
    "GNV": "#eda100", "GLP": "#e87ba4",
}
COR_PRINCIPAL = "#2a78d6"
COR_DESTAQUE = "#eb6834"
COR_NEUTRA = "#898781"
ESCALA_SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ESCALA_DIVERGENTE = [[0, "#2a78d6"], [0.5, "#f0efec"], [1, "#e34948"]]

CSS = """
<style>
:root {
  --ink-1: #1d1d1f; --ink-2: #6e6e73; --hair: rgba(0,0,0,.08);
  --card: rgba(255,255,255,.72); --accent: #2a78d6; --accent-2: #eb6834;
}
html, body, [class*="css"], .stMarkdown, .stText {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
}
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 4.2rem !important; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.02em; }

.hero-eyebrow { font-size: .78rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent-2); margin-bottom: .25rem; }
.hero-title { font-size: clamp(1.9rem, 3.6vw, 2.9rem); font-weight: 700;
  line-height: 1.06; letter-spacing: -0.03em; margin: 0 0 .6rem; }
.hero-sub { font-size: 1.08rem; line-height: 1.55; color: var(--ink-2); max-width: 62ch; }

.kpi-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  margin: 1.2rem 0 1.6rem; }
.kpi { background: var(--card); backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid var(--hair); border-radius: 18px; padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 8px 24px rgba(0,0,0,.04);
  transition: transform 160ms ease-out, box-shadow 160ms ease-out; }
.kpi:hover { transform: translateY(-2px); box-shadow: 0 2px 4px rgba(0,0,0,.05), 0 14px 32px rgba(0,0,0,.07); }
.kpi-label { font-size: .78rem; font-weight: 500; color: var(--ink-2); letter-spacing: .01em; }
.kpi-value { font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.2;
  margin-top: 4px; color: var(--ink-1); }
.kpi-note { font-size: .78rem; color: var(--ink-2); margin-top: 2px; }

.insight { border-left: 3px solid var(--accent); background: var(--card);
  border-radius: 0 14px 14px 0; padding: 14px 18px; margin: .6rem 0 1.4rem;
  line-height: 1.6; font-size: .97rem; }
.insight b { color: var(--ink-1); }
.insight-title { font-size: .74rem; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 4px; }
.aviso { border-left-color: var(--accent-2); }
.aviso .insight-title { color: var(--accent-2); }

.secao { font-size: 1.35rem; font-weight: 650; letter-spacing: -0.015em; margin: 1.6rem 0 .2rem; }
.secao-sub { color: var(--ink-2); font-size: .93rem; margin-bottom: .6rem; }

[data-testid="stSidebar"] { border-right: 1px solid var(--hair); }
.stButton > button:active { transform: scale(.97); }
@media (prefers-reduced-motion: reduce) { .kpi, .kpi:hover { transition: none; transform: none; } }
</style>
"""


def aplicar_estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(eyebrow: str, titulo: str, subtitulo: str) -> None:
    st.markdown(
        f'<div class="hero-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1 class="hero-title">{html.escape(titulo)}</h1>'
        f'<p class="hero-sub">{subtitulo}</p>',
        unsafe_allow_html=True,
    )


def secao(titulo: str, sub: str = "") -> None:
    st.markdown(f'<div class="secao">{html.escape(titulo)}</div>'
                + (f'<div class="secao-sub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def cartoes_kpi(itens: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        f'<div class="kpi"><div class="kpi-label">{html.escape(r)}</div>'
        f'<div class="kpi-value">{html.escape(v)}</div>'
        f'<div class="kpi-note">{html.escape(n)}</div></div>'
        for r, v, n in itens
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def interpretacao(texto: str, titulo: str = "Interpretação", aviso: bool = False) -> None:
    classe = "insight aviso" if aviso else "insight"
    st.markdown(f'<div class="{classe}"><div class="insight-title">{html.escape(titulo)}</div>'
                f'{texto}</div>', unsafe_allow_html=True)


def layout_grafico(fig: go.Figure, altura: int = 380, titulo_y: str | None = None,
                   titulo_x: str | None = None, legenda: bool = True) -> go.Figure:
    fig.update_layout(
        height=altura, margin=dict(l=8, r=8, t=36, b=8),
        font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif", size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        showlegend=legenda, hoverlabel=dict(font_size=13),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, title_text=titulo_x)
    fig.update_yaxes(gridwidth=1, zeroline=False, title_text=titulo_y)
    return fig


def sem_dados() -> None:
    st.info("Nenhum registro com os filtros atuais. Amplie a seleção na barra lateral.")
