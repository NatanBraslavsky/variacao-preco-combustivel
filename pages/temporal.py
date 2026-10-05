import matplotlib.pyplot as plt
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st

from src.dados import NOMES_MESES, fmt_brl, fmt_num, indicadores_mensais
from src.ui import (COR_DESTAQUE, COR_NEUTRA, COR_PRINCIPAL, CORES_COMBUSTIVEL, cabecalho,
                    interpretacao, layout_grafico, secao, sem_dados)

df = st.session_state["df"]
cabecalho("Análise temporal", "Evolução dos preços",
          "Evolução por combustível, sazonalidade mês a mês e identificação dos períodos "
          "de maior instabilidade.")
if df.empty:
    sem_dados()
    st.stop()

# ------------------------------------------------------------ linha temporal
secao("Linha temporal por combustível")
granularidade = st.segmented_control("Granularidade", ["Mensal", "Trimestral", "Anual"],
                                     default="Trimestral", key="granularidade")
regra = {"Mensal": "MS", "Trimestral": "QS", "Anual": "YS"}[granularidade or "Trimestral"]
serie = (df.groupby(["combustivel", df["data"].dt.to_period(regra[0]).dt.start_time],
                    observed=True)["preco_medio"].mean().reset_index())
fig = go.Figure()
for comb, g in serie.groupby("combustivel", observed=True):
    fig.add_scatter(x=g["data"], y=g["preco_medio"], name=str(comb), mode="lines",
                    line=dict(color=CORES_COMBUSTIVEL[str(comb)], width=2),
                    hovertemplate=f"{comb}: R$ %{{y:.2f}}<extra></extra>")
fig.update_layout(hovermode="x unified")
st.plotly_chart(layout_grafico(fig, 400, "R$ por unidade"), width="stretch")

anual = df.groupby("ano")["preco_medio"].mean()
interpretacao(
    f"Na visão anual, o preço médio vai de <b>{fmt_brl(anual.min())}</b> ({anual.idxmin()}) a "
    f"<b>{fmt_brl(anual.max())}</b> ({anual.idxmax()}) — uma faixa de apenas "
    f"{fmt_num((anual.max() / anual.min() - 1) * 100, 1)}%. As linhas dos combustíveis se cruzam "
    "o tempo todo: nenhum combustível é sistematicamente mais caro. Quanto mais fina a "
    "granularidade, maior o ruído — típico de dados sem tendência."
)

# ------------------------------------------------------------ heatmap mensal (seaborn)
c1, c2 = st.columns([3, 2])
with c1:
    secao("Heatmap mensal do preço médio", "Ano × mês — Seaborn. Tons mais escuros = preço maior.")
    tabela = df.pivot_table(index="ano", columns="mes", values="preco_medio", aggfunc="mean")
    tabela.columns = [NOMES_MESES[c - 1] for c in tabela.columns]
    fig_h, ax = plt.subplots(figsize=(9, 4.6))
    sns.heatmap(tabela, cmap="Blues", annot=True, fmt=".2f", annot_kws={"size": 7.5},
                linewidths=1.5, linecolor="white", cbar_kws={"label": "R$"}, ax=ax)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(length=0)
    fig_h.tight_layout()
    st.pyplot(fig_h, width="stretch")
    plt.close(fig_h)
with c2:
    secao("Sazonalidade", "Preço médio por mês do ano (todos os anos).")
    saz = df.groupby("mes")["preco_medio"].mean()
    fig = go.Figure(go.Bar(
        x=[NOMES_MESES[i - 1] for i in saz.index], y=saz.values,
        marker=dict(color=[COR_DESTAQUE if v == saz.max() else COR_PRINCIPAL for v in saz.values],
                    cornerradius=4),
        hovertemplate="%{x}: R$ %{y:.3f}<extra></extra>"))
    fig.update_yaxes(range=[saz.min() * .97, saz.max() * 1.015])
    st.plotly_chart(layout_grafico(fig, 400, legenda=False), width="stretch")

interpretacao(
    f"O mês historicamente mais caro é <b>{NOMES_MESES[saz.idxmax() - 1]}</b> "
    f"({fmt_brl(saz.max())}) e o mais barato, <b>{NOMES_MESES[saz.idxmin() - 1]}</b> "
    f"({fmt_brl(saz.min())}). A diferença é pequena e o heatmap não mostra faixas verticais "
    "consistentes (o mesmo mês caro em vários anos), portanto <b>não há sazonalidade clara</b>."
)

# ------------------------------------------------------------ períodos críticos
secao("Períodos de maior instabilidade",
      "Volatilidade = desvio padrão da variação mensal entre estados e combustíveis no mês.")
m = indicadores_mensais(df)
limite = m["volatilidade"].quantile(.9)
fig = go.Figure()
fig.add_bar(x=m["data"], y=m["volatilidade"], name="Volatilidade",
            marker=dict(color=[COR_DESTAQUE if v >= limite else "#9ec5f4" for v in m["volatilidade"]],
                        cornerradius=2),
            hovertemplate="%{x|%b/%Y}<br>Volatilidade: %{y:.2f} p.p.<extra></extra>")
fig.add_hline(y=limite, line=dict(color=COR_NEUTRA, width=1),
              annotation_text="10% mais instáveis", annotation_position="top left")
st.plotly_chart(layout_grafico(fig, 320, "desvio padrão (p.p.)", legenda=False), width="stretch")

top = m.nlargest(5, "volatilidade")[["data", "volatilidade", "variacao_media", "pct_critico", "preco_medio"]]
top["data"] = top["data"].dt.strftime("%m/%Y")
st.dataframe(
    top.rename(columns={"data": "Mês", "volatilidade": "Volatilidade (p.p.)",
                        "variacao_media": "Variação média (%)", "pct_critico": "% nível Crítico",
                        "preco_medio": "Preço médio (R$)"}),
    hide_index=True, width="stretch",
    column_config={c: st.column_config.NumberColumn(format="%.2f")
                   for c in ["Volatilidade (p.p.)", "Variação média (%)", "% nível Crítico", "Preço médio (R$)"]},
)
anos_top = m[m["volatilidade"] >= limite]["data"].dt.year.value_counts()
interpretacao(
    f"Os meses mais instáveis estão destacados em laranja. O pico ocorre em "
    f"<b>{m.loc[m['volatilidade'].idxmax(), 'data']:%m/%Y}</b> "
    f"({fmt_num(m['volatilidade'].max(), 2)} p.p.). Eles aparecem espalhados por "
    f"{anos_top.size} anos diferentes, sem se concentrar em uma crise específica — "
    "diferente dos dados reais, em que 2021–2022 (pós-pandemia e guerra na Ucrânia) "
    "dominariam o ranking."
)
