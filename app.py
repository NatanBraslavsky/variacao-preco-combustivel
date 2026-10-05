"""Dashboard — Variação dos Preços de Combustíveis no Brasil (2015–2024).

Ponto de entrada do Streamlit. Carrega a base (CSV → SQLite), monta os filtros
compartilhados na barra lateral e despacha para as páginas em pages/.

Execução local:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.api_bcb import obter_ipca
from src.banco import CAMINHO_DB, construir_banco, obter_engine
from src.dados import (NOMES_MESES, ORDEM_COMBUSTIVEIS, ORDEM_NIVEIS, ORDEM_REGIOES,
                       preparar)
from src.ui import aplicar_estilo

st.set_page_config(
    page_title="Combustíveis no Brasil · Dashboard",
    page_icon=":material/local_gas_station:",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo()


@st.cache_data(show_spinner="Carregando e tratando a base…")
def carregar_base() -> pd.DataFrame:
    return preparar()


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Consultando a API do Banco Central…")
def carregar_ipca() -> tuple[pd.DataFrame, str]:
    return obter_ipca()


@st.cache_resource(show_spinner="Preparando o banco SQLite…")
def carregar_engine():
    engine = obter_engine()
    if not CAMINHO_DB.exists() or CAMINHO_DB.stat().st_size == 0:
        construir_banco(carregar_base(), engine, carregar_ipca()[0])
    return engine


base = st.session_state.get("df_upload")
fonte = st.session_state.get("nome_upload", "simulacao_precos_combustiveis_brasil.csv")
if base is None:
    base = carregar_base()
ipca, origem_ipca = carregar_ipca()
st.session_state.update(df_base=base, ipca=ipca, origem_ipca=origem_ipca,
                        engine=carregar_engine(), fonte=fonte)

# ---------------------------------------------------------------- filtros
FILTROS = ["f_anos", "f_meses", "f_regioes", "f_ufs", "f_combustiveis", "f_niveis"]


def limpar_filtros() -> None:
    for chave in FILTROS:
        st.session_state.pop(chave, None)


anos = sorted(base["ano"].unique())
with st.sidebar:
    st.markdown("### Filtros")
    st.caption("Deixe um campo vazio para considerar todas as opções.")
    faixa_anos = st.slider("Ano", int(anos[0]), int(anos[-1]),
                           (int(anos[0]), int(anos[-1])), key="f_anos")
    meses = st.multiselect("Mês", NOMES_MESES, key="f_meses", placeholder="Todos")
    regioes = st.multiselect("Região", ORDEM_REGIOES, key="f_regioes", placeholder="Todas")
    opcoes_uf = sorted(base.loc[base["regiao"].isin(regioes), "uf"].unique()
                       if regioes else base["uf"].unique())
    st.session_state["f_ufs"] = [u for u in st.session_state.get("f_ufs", []) if u in opcoes_uf]
    ufs = st.multiselect("Estado (UF)", opcoes_uf, key="f_ufs", placeholder="Todos")
    combustiveis = st.multiselect("Combustível", ORDEM_COMBUSTIVEIS, key="f_combustiveis",
                                  placeholder="Todos")
    niveis = st.multiselect("Nível de preço", ORDEM_NIVEIS, key="f_niveis", placeholder="Todos",
                            help="Classificação original da base (coluna nivel_preco).")
    st.button("Limpar filtros", on_click=limpar_filtros, width="stretch",
              icon=":material/filter_alt_off:")

mascara = base["ano"].between(*faixa_anos)
if meses:
    mascara &= base["mes"].isin([NOMES_MESES.index(m) + 1 for m in meses])
if regioes:
    mascara &= base["regiao"].isin(regioes)
if ufs:
    mascara &= base["uf"].isin(ufs)
if combustiveis:
    mascara &= base["combustivel"].isin(combustiveis)
if niveis:
    mascara &= base["nivel_preco"].isin(niveis)
df = base[mascara]
st.session_state["df"] = df

with st.sidebar:
    st.divider()
    st.caption(f"**{len(df):,}** de {len(base):,} registros selecionados".replace(",", "."))
    st.caption(f"Base: `{fonte}`  \nIPCA: {origem_ipca}")

# ---------------------------------------------------------------- navegação
paginas = {
    "Painel": [
        st.Page("pages/visao_geral.py", title="Visão geral", icon=":material/dashboard:", default=True),
        st.Page("pages/temporal.py", title="Evolução temporal", icon=":material/timeline:"),
        st.Page("pages/regional.py", title="Regiões e estados", icon=":material/map:"),
        st.Page("pages/combustiveis.py", title="Combustíveis", icon=":material/local_gas_station:"),
        st.Page("pages/economia.py", title="Inflação e petróleo", icon=":material/query_stats:"),
    ],
    "Análise": [
        st.Page("pages/dados.py", title="Dados e SQL", icon=":material/table_view:"),
        st.Page("pages/conclusoes.py", title="Conclusões", icon=":material/task_alt:"),
    ],
}
st.navigation(paginas).run()
