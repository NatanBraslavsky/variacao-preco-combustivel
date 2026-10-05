import json

import plotly.graph_objects as go
import streamlit as st

from src.dados import CAMINHO_GEOJSON, ORDEM_REGIOES, fmt_brl, fmt_num
from src.ui import (COR_DESTAQUE, COR_PRINCIPAL, ESCALA_DIVERGENTE, ESCALA_SEQUENCIAL, cabecalho,
                    interpretacao, layout_grafico, secao, sem_dados)


@st.cache_data
def carregar_geojson() -> dict:
    return json.loads(CAMINHO_GEOJSON.read_text(encoding="utf-8"))


df = st.session_state["df"]
cabecalho("Análise geográfica", "Preços por região e estado",
          "Comparação entre os 20 estados e as 5 regiões presentes na base, com mapa interativo.")
if df.empty:
    sem_dados()
    st.stop()

por_uf = (df.groupby(["uf", "nome_uf", "regiao"], observed=True)
            .agg(preco_medio=("preco_medio", "mean"), registros=("preco_medio", "size"),
                 variacao=("variacao_mensal", "mean"))
            .reset_index().sort_values("preco_medio", ascending=False))

# ------------------------------------------------------------ mapa
c1, c2 = st.columns([3, 2])
with c1:
    secao("Mapa do preço médio por estado", "Estados em cinza não constam na base.")
    geo = carregar_geojson()
    todas = [f["properties"]["sigla"] for f in geo["features"]]
    fig = go.Figure()
    fig.add_choropleth(geojson=geo, locations=todas, z=[0] * len(todas),
                       featureidkey="properties.sigla", showscale=False, hoverinfo="skip",
                       colorscale=[[0, "#e8e8ed"], [1, "#e8e8ed"]],
                       marker_line=dict(color="white", width=1))
    fig.add_choropleth(geojson=geo, locations=por_uf["uf"], z=por_uf["preco_medio"],
                       featureidkey="properties.sigla", colorscale=ESCALA_SEQUENCIAL,
                       marker_line=dict(color="white", width=1),
                       customdata=por_uf[["nome_uf", "regiao", "registros"]],
                       colorbar=dict(title="R$", thickness=10, len=.7),
                       hovertemplate="<b>%{customdata[0]}</b> (%{location})<br>%{customdata[1]}"
                                     "<br>Preço médio: R$ %{z:.3f}<br>Registros: %{customdata[2]}"
                                     "<extra></extra>")
    fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                    lonaxis_range=[-74.5, -34.5], lataxis_range=[-34, 5.5])
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), dragmode=False)
    st.plotly_chart(fig, width="stretch", config={"scrollZoom": False})
with c2:
    secao("Ranking dos estados")
    ordem = por_uf.sort_values("preco_medio")
    fig = go.Figure(go.Bar(
        x=ordem["preco_medio"], y=ordem["uf"], orientation="h",
        marker=dict(color=[COR_DESTAQUE if i >= len(ordem) - 3 else COR_PRINCIPAL
                           for i in range(len(ordem))], cornerradius=3),
        customdata=ordem[["nome_uf", "regiao"]],
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>R$ %{x:.3f}<extra></extra>"))
    fig.update_xaxes(range=[ordem["preco_medio"].min() * .95, ordem["preco_medio"].max() * 1.01])
    st.plotly_chart(layout_grafico(fig, 520, legenda=False), width="stretch")

topo, base_ = por_uf.iloc[0], por_uf.iloc[-1]
interpretacao(
    f"<b>{topo['nome_uf']}</b> tem o maior preço médio ({fmt_brl(topo['preco_medio'])}) e "
    f"<b>{base_['nome_uf']}</b>, o menor ({fmt_brl(base_['preco_medio'])}): diferença de "
    f"<b>{fmt_num((topo['preco_medio'] / base_['preco_medio'] - 1) * 100, 1)}%</b>. Os três mais "
    "caros estão em laranja. Atenção: alguns estados têm o dobro de registros de outros "
    "(amostragem desigual), o que torna suas médias mais estáveis."
)

# ------------------------------------------------------------ regiões
c1, c2 = st.columns(2)
with c1:
    secao("Distribuição dos preços por região", "Caixa = 50% centrais; linha = mediana.")
    fig = go.Figure()
    for reg in ORDEM_REGIOES:
        vals = df.loc[df["regiao"] == reg, "preco_medio"]
        if len(vals):
            fig.add_box(y=vals, name=reg, marker_color=COR_PRINCIPAL, line_width=1.5,
                        boxmean=True, hovertemplate="R$ %{y:.2f}<extra></extra>")
    st.plotly_chart(layout_grafico(fig, 380, "R$ por unidade", legenda=False), width="stretch")
with c2:
    secao("Região × combustível", "Diferença (%) em relação à média do recorte.")
    media = df["preco_medio"].mean()
    tab = df.pivot_table(index="regiao", columns="combustivel", values="preco_medio",
                         aggfunc="mean", observed=True)
    desvio = (tab / media - 1) * 100
    lim = max(abs(desvio.min().min()), abs(desvio.max().max()))
    fig = go.Figure(go.Heatmap(
        z=desvio.values, x=desvio.columns.astype(str), y=desvio.index.astype(str),
        colorscale=ESCALA_DIVERGENTE, zmin=-lim, zmax=lim, xgap=2, ygap=2,
        text=desvio.round(1).astype(str).values, texttemplate="%{text}%",
        customdata=tab.values,
        hovertemplate="%{y} · %{x}<br>R$ %{customdata:.3f} (%{z:+.1f}%)<extra></extra>",
        colorbar=dict(title="%", thickness=10)))
    st.plotly_chart(layout_grafico(fig, 380, legenda=False), width="stretch")

por_reg = df.groupby("regiao", observed=True)["preco_medio"].agg(["mean", "median", "std"])
interpretacao(
    f"A região mais cara é o <b>{por_reg['mean'].idxmax()}</b> ({fmt_brl(por_reg['mean'].max())}) e a "
    f"mais barata, o <b>{por_reg['mean'].idxmin()}</b> ({fmt_brl(por_reg['mean'].min())}). As caixas "
    "se sobrepõem quase totalmente: a dispersão <i>dentro</i> de cada região (desvio ≈ "
    f"{fmt_brl(por_reg['std'].mean())}) é muito maior que a diferença <i>entre</i> regiões. "
    "Em vermelho, combinações acima da média; em azul, abaixo. "
    "<b>As diferenças regionais existem, mas não são relevantes</b> do ponto de vista estatístico."
)

st.dataframe(
    por_uf.rename(columns={"uf": "UF", "nome_uf": "Estado", "regiao": "Região",
                           "preco_medio": "Preço médio (R$)", "registros": "Registros",
                           "variacao": "Variação média (%)"}),
    hide_index=True, width="stretch",
    column_config={"Preço médio (R$)": st.column_config.NumberColumn(format="%.3f"),
                   "Variação média (%)": st.column_config.NumberColumn(format="%.2f")},
)
