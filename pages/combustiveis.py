import plotly.graph_objects as go
import streamlit as st

from src.dados import aumento_periodo, fmt_brl, fmt_num, volatilidade_por
from src.ui import (COR_NEUTRA, CORES_COMBUSTIVEL, cabecalho, interpretacao, layout_grafico,
                    secao, sem_dados)

df = st.session_state["df"]
cabecalho("Comparação energética", "Preços por combustível",
          "Preço, aumento acumulado e volatilidade de cada combustível no recorte filtrado.")
if df.empty:
    sem_dados()
    st.stop()

vol = volatilidade_por(df, "combustivel")
vol["combustivel"] = vol["combustivel"].astype(str)
cores = [CORES_COMBUSTIVEL[c] for c in vol["combustivel"]]

c1, c2 = st.columns(2)
with c1:
    secao("Preço médio por combustível", "Barra = média; traço = desvio padrão.")
    ordem = vol.sort_values("preco_medio", ascending=False)
    fig = go.Figure(go.Bar(
        x=ordem["combustivel"], y=ordem["preco_medio"],
        marker=dict(color=[CORES_COMBUSTIVEL[c] for c in ordem["combustivel"]], cornerradius=4),
        error_y=dict(type="data", array=ordem["desvio_preco"], color=COR_NEUTRA, thickness=1.2, width=6),
        text=[fmt_brl(v) for v in ordem["preco_medio"]], textposition="inside",
        insidetextanchor="end", textfont=dict(color="white"),
        hovertemplate="%{x}<br>Média: R$ %{y:.3f}<extra></extra>"))
    st.plotly_chart(layout_grafico(fig, 380, "R$ por unidade", legenda=False), width="stretch")
with c2:
    aum = aumento_periodo(df)
    anos = sorted(df["ano"].unique())
    secao("Aumento acumulado no período",
          f"Variação do preço médio entre {anos[0]} e {anos[-1]}." if len(anos) > 1 else "")
    if aum.empty:
        st.info("Selecione pelo menos dois anos para calcular o aumento.")
    else:
        aum["combustivel"] = aum["combustivel"].astype(str)
        fig = go.Figure(go.Bar(
            x=aum["aumento_pct"], y=aum["combustivel"], orientation="h",
            marker=dict(color=[CORES_COMBUSTIVEL[c] for c in aum["combustivel"]], cornerradius=4),
            text=[f"{v:+.1f}%".replace(".", ",") for v in aum["aumento_pct"]], textposition="outside",
            customdata=aum[["inicio", "fim"]],
            hovertemplate="%{y}<br>R$ %{customdata[0]:.2f} → R$ %{customdata[1]:.2f}"
                          "<br>%{x:+.2f}%<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=0, line=dict(color=COR_NEUTRA, width=1))
        st.plotly_chart(layout_grafico(fig, 380, titulo_x="%", legenda=False), width="stretch")

mais_caro = vol.loc[vol["preco_medio"].idxmax()]
mais_barato = vol.loc[vol["preco_medio"].idxmin()]
txt_aum = ""
if not aum.empty:
    txt_aum = (f" O maior aumento acumulado foi do <b>{aum.iloc[0]['combustivel']}</b> "
               f"({fmt_num(aum.iloc[0]['aumento_pct'], 1)}%), e o menor, do "
               f"<b>{aum.iloc[-1]['combustivel']}</b> ({fmt_num(aum.iloc[-1]['aumento_pct'], 1)}%).")
interpretacao(
    f"O <b>{mais_caro['combustivel']}</b> é o mais caro em média ({fmt_brl(mais_caro['preco_medio'])}) "
    f"e o <b>{mais_barato['combustivel']}</b>, o mais barato ({fmt_brl(mais_barato['preco_medio'])}) — "
    f"diferença de só {fmt_num((mais_caro['preco_medio'] / mais_barato['preco_medio'] - 1) * 100, 1)}%. "
    "Os traços de desvio padrão se sobrepõem, então o ranking é instável." + txt_aum +
    " Comparando só o primeiro e o último ano, o resultado é sensível a anos atípicos — "
    "por isso ele muda bastante conforme os filtros."
)

secao("Volatilidade", "Quanto o preço oscila de um mês para o outro.")
c1, c2 = st.columns([2, 3])
with c1:
    ordem = vol.sort_values("desvio_variacao", ascending=False)
    fig = go.Figure(go.Bar(
        x=ordem["combustivel"], y=ordem["desvio_variacao"],
        marker=dict(color=[CORES_COMBUSTIVEL[c] for c in ordem["combustivel"]], cornerradius=4),
        hovertemplate="%{x}<br>Desvio da variação mensal: %{y:.2f} p.p.<extra></extra>"))
    fig.update_yaxes(range=[ordem["desvio_variacao"].min() * .9, ordem["desvio_variacao"].max() * 1.03])
    st.plotly_chart(layout_grafico(fig, 360, "desvio padrão (p.p.)", legenda=False), width="stretch")
with c2:
    fig = go.Figure()
    for comb in vol["combustivel"]:
        fig.add_violin(y=df.loc[df["combustivel"] == comb, "variacao_mensal"], name=comb,
                       line_color=CORES_COMBUSTIVEL[comb], box_visible=True, meanline_visible=True,
                       points=False, hoveron="kde")
    fig.add_hline(y=0, line=dict(color=COR_NEUTRA, width=1))
    st.plotly_chart(layout_grafico(fig, 360, "variação mensal (%)", legenda=False), width="stretch")

mais_vol = vol.loc[vol["desvio_variacao"].idxmax()]
menos_vol = vol.loc[vol["desvio_variacao"].idxmin()]
interpretacao(
    f"O combustível mais volátil é o <b>{mais_vol['combustivel']}</b> (desvio de "
    f"{fmt_num(mais_vol['desvio_variacao'], 2)} p.p. na variação mensal) e o mais estável, o "
    f"<b>{menos_vol['combustivel']}</b> ({fmt_num(menos_vol['desvio_variacao'], 2)} p.p.). As "
    "distribuições (violinos) são praticamente idênticas e simétricas em torno de zero, com altas e "
    "quedas de até ±15% — volatilidade alta, porém <b>igual para todos os combustíveis</b>."
)

st.dataframe(
    vol.rename(columns={"combustivel": "Combustível", "preco_medio": "Preço médio (R$)",
                        "desvio_preco": "Desvio do preço (R$)", "cv_pct": "Coef. de variação (%)",
                        "desvio_variacao": "Desvio var. mensal (p.p.)", "maior_alta": "Maior alta (%)",
                        "maior_queda": "Maior queda (%)", "registros": "Registros"}),
    hide_index=True, width="stretch",
)
