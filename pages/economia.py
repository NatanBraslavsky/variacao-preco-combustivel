import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st

from src.dados import fmt_num, indicadores_mensais
from src.ui import (COR_DESTAQUE, COR_NEUTRA, COR_PRINCIPAL, cabecalho, interpretacao,
                    layout_grafico, secao, sem_dados)

df = st.session_state["df"]
ipca = st.session_state["ipca"]
cabecalho("Correlação estatística", "Preço, inflação e petróleo",
          "Dispersões, matriz de correlação e comparação com o IPCA real obtido da API do "
          "Banco Central.")
if df.empty or len(df) < 10:
    sem_dados()
    st.stop()


def forca(r: float) -> str:
    a = abs(r)
    return ("muito fraca" if a < .1 else "fraca" if a < .3 else "moderada" if a < .5
            else "forte" if a < .7 else "muito forte")


def dispersao(x: str, rotulo_x: str, cor: str) -> tuple[go.Figure, float]:
    amostra = df.sample(min(len(df), 1500), random_state=42)
    r = df[x].corr(df["preco_medio"])
    a, b = np.polyfit(df[x], df["preco_medio"], 1)
    xs = np.linspace(df[x].min(), df[x].max(), 50)
    fig = go.Figure()
    fig.add_scatter(x=amostra[x], y=amostra["preco_medio"], mode="markers", name="Registros",
                    marker=dict(color=cor, size=6, opacity=.35, line=dict(width=0)),
                    hovertemplate=f"{rotulo_x}: %{{x:.2f}}<br>Preço: R$ %{{y:.2f}}<extra></extra>")
    fig.add_scatter(x=xs, y=a * xs + b, mode="lines", name="Tendência linear",
                    line=dict(color="#1d1d1f", width=2), hoverinfo="skip")
    fig.update_layout(title=dict(text=f"r de Pearson = {r:+.3f}".replace(".", ","),
                                 font=dict(size=13), x=0, y=.99))
    return layout_grafico(fig, 380, "Preço médio (R$)", rotulo_x), r


c1, c2 = st.columns(2)
with c1:
    secao("Dispersão inflação × preço")
    fig, r_inf = dispersao("inflacao", "Inflação (%)", COR_PRINCIPAL)
    st.plotly_chart(fig, width="stretch")
with c2:
    secao("Dispersão petróleo × preço")
    fig, r_pet = dispersao("cotacao_petroleo", "Cotação do petróleo (US$)", COR_DESTAQUE)
    st.plotly_chart(fig, width="stretch")

limiar = 2 / np.sqrt(len(df))
interpretacao(
    f"A correlação entre inflação e preço é <b>{fmt_num(r_inf, 3)}</b> ({forca(r_inf)}) e entre "
    f"petróleo e preço, <b>{fmt_num(r_pet, 3)}</b> ({forca(r_pet)}). Com {fmt_num(len(df))} registros, "
    f"valores abaixo de ±{fmt_num(limiar, 3)} não se distinguem do acaso (≈95% de confiança). "
    "As nuvens de pontos são retângulos uniformes e a reta de tendência é praticamente horizontal: "
    "<b>nesta base, nem inflação nem petróleo explicam o preço dos combustíveis.</b>"
)

c1, c2 = st.columns([1, 1])
with c1:
    secao("Matriz de correlação", "Seaborn · registros individuais.")
    metodo = st.segmented_control("Método", ["pearson", "spearman"], default="pearson",
                                  format_func=str.capitalize, key="metodo_corr") or "pearson"
    cols = {"preco_medio": "Preço", "variacao_mensal": "Variação", "inflacao": "Inflação",
            "cotacao_petroleo": "Petróleo", "consumo_estimado": "Consumo", "amplitude": "Amplitude"}
    base_corr = df[list(cols)].rename(columns=cols)
    corr = (base_corr.rank() if metodo == "spearman" else base_corr).corr()
    fig_c, ax = plt.subplots(figsize=(6, 4.8))
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mascara, cmap="RdBu_r", vmin=-1, vmax=1, center=0, annot=True,
                fmt=".2f", linewidths=2, linecolor="white", square=True,
                cbar_kws={"shrink": .75}, ax=ax)
    ax.tick_params(length=0)
    fig_c.tight_layout()
    st.pyplot(fig_c, width="stretch")
    plt.close(fig_c)
with c2:
    secao("Correlação na série mensal", "Médias nacionais por mês (120 pontos).")
    m = indicadores_mensais(df)
    pares = {
        "Preço × inflação": m["preco_medio"].corr(m["inflacao"]),
        "Preço × petróleo": m["preco_medio"].corr(m["cotacao_petroleo"]),
        "Preço × volatilidade": m["preco_medio"].corr(m["volatilidade"]),
        "Inflação × petróleo": m["inflacao"].corr(m["cotacao_petroleo"]),
    }
    fig = go.Figure(go.Bar(
        x=list(pares.values()), y=list(pares.keys()), orientation="h",
        marker=dict(color=[COR_DESTAQUE if v > 0 else COR_PRINCIPAL for v in pares.values()],
                    cornerradius=4),
        text=[f"{v:+.3f}".replace(".", ",") for v in pares.values()], textposition="outside",
        hovertemplate="%{y}: r = %{x:+.3f}<extra></extra>"))
    fig.update_xaxes(range=[-1, 1])
    fig.add_vline(x=0, line=dict(color=COR_NEUTRA, width=1))
    lim_m = 2 / np.sqrt(len(m))
    for s in (-lim_m, lim_m):
        fig.add_vline(x=s, line=dict(color=COR_NEUTRA, width=1), opacity=.5)
    st.plotly_chart(layout_grafico(fig, 380, titulo_x="r de Pearson", legenda=False), width="stretch")

interpretacao(
    "Na matriz, praticamente todas as células fora da diagonal ficam próximas de zero; a única "
    "relação forte é <b>preço × amplitude</b>, que é estrutural (amplitude = máximo − mínimo, "
    "proporcional ao preço). Mesmo agregando por mês — o que remove ruído individual — as "
    "correlações continuam dentro da faixa do acaso (linhas cinza). Pearson e Spearman concordam, "
    "então não há relação não linear escondida."
)

secao("Inflação simulada × IPCA real (API do Banco Central)",
      f"Série SGS 13522 — IPCA acumulado em 12 meses. Fonte: {st.session_state['origem_ipca']}.")
if ipca.empty:
    st.warning("Não foi possível obter o IPCA (API e cópia local indisponíveis).")
else:
    m_full = indicadores_mensais(df).merge(ipca, on="data", how="left")
    fig = go.Figure()
    fig.add_scatter(x=m_full["data"], y=m_full["ipca_12m"], name="IPCA real 12 meses (BCB)",
                    line=dict(color=COR_DESTAQUE, width=2.5),
                    hovertemplate="%{x|%b/%Y}: %{y:.2f}%<extra></extra>")
    fig.add_scatter(x=m_full["data"], y=m_full["inflacao"], name="Inflação da base simulada",
                    line=dict(color=COR_PRINCIPAL, width=1.5),
                    hovertemplate="%{x|%b/%Y}: %{y:.2f}%<extra></extra>")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(layout_grafico(fig, 360, "% ao ano"), width="stretch")
    r_ipca = m_full["inflacao"].corr(m_full["ipca_12m"])
    pico = m_full.loc[m_full["ipca_12m"].idxmax()] if m_full["ipca_12m"].notna().any() else None
    interpretacao(
        "O IPCA real mostra ciclos econômicos claros: alta em 2015–2016 (recessão), mínima em "
        "2017–2020 e o choque de 2021–2022"
        + (f", com pico de <b>{fmt_num(pico['ipca_12m'], 2)}%</b> em {pico['data']:%m/%Y}" if pico is not None else "")
        + f". A inflação da base simulada oscila aleatoriamente em torno de 7% e tem correlação de "
        f"<b>{fmt_num(r_ipca, 2)}</b> com o IPCA real. Integrar essa fonte externa confirma que a base "
        "não reproduz a dinâmica macroeconômica brasileira — na vida real, o choque de 2021–2022 foi "
        "puxado justamente pelos combustíveis.",
        titulo="Integração de fontes (CSV + API + banco)",
    )
