import plotly.graph_objects as go
import streamlit as st

from src.dados import NOMES_UF, fmt_brl, fmt_compacto, fmt_num, indicadores_mensais, kpis
from src.ui import (COR_DESTAQUE, COR_NEUTRA, COR_PRINCIPAL, CORES_COMBUSTIVEL, cabecalho,
                    cartoes_kpi, interpretacao, layout_grafico, secao, sem_dados)

df = st.session_state["df"]

cabecalho(
    "Projeto G1 · Análise e Visualização de Dados com Python",
    "Variação dos Preços de Combustíveis no Brasil",
    "Os combustíveis afetam transporte, logística, inflação e custo de vida. Este painel "
    "investiga a evolução dos preços de <b>gasolina, etanol, diesel, GNV e GLP</b> entre "
    "<b>2015 e 2024</b> em 20 estados das 5 regiões, comparando territórios, combustíveis, "
    "períodos de alta e a relação com a inflação e o petróleo.",
)

if df.empty:
    sem_dados()
    st.stop()

k = kpis(df)
cartoes_kpi([
    ("Preço médio nacional", fmt_brl(k["preco_medio_nacional"]), "média geral do período filtrado"),
    ("Combustível mais caro", k["combustivel_mais_caro"], fmt_brl(k["combustivel_mais_caro_preco"]) + " em média"),
    ("Estado com maior preço", NOMES_UF.get(k["uf_mais_cara"], k["uf_mais_cara"]),fmt_brl(k["uf_mais_cara_preco"]) + " em média"),
    ("Maior variação mensal", fmt_num(k["maior_variacao"], 2).replace("-", "−") + "%", k["maior_variacao_desc"]),
    ("Consumo estimado total", fmt_compacto(k["consumo_total"]), "unidades no período"),
    ("Região mais cara", k["regiao_mais_cara"], fmt_brl(k["regiao_mais_cara_preco"]) + " em média"),
])

secao("Preço médio nacional ao longo do tempo",
      "Média mensal de todos os estados e combustíveis selecionados, com média móvel de 12 meses.")
m = indicadores_mensais(df)
fig = go.Figure()
fig.add_scatter(x=m["data"], y=m["preco_medio"], name="Preço médio mensal", mode="lines",
                line=dict(color=COR_PRINCIPAL, width=1.5), opacity=.55,
                hovertemplate="%{x|%b/%Y}<br>R$ %{y:.2f}<extra></extra>")
fig.add_scatter(x=m["data"], y=m["media_movel_12m"], name="Média móvel 12 meses", mode="lines",
                line=dict(color=COR_DESTAQUE, width=2.5),
                hovertemplate="%{x|%b/%Y}<br>R$ %{y:.2f}<extra></extra>")
fig.add_hline(y=m["preco_medio"].mean(), line=dict(color=COR_NEUTRA, width=1),
              annotation_text="média do período", annotation_position="top left")
fig.update_layout(hovermode="x unified")
st.plotly_chart(layout_grafico(fig, 360, "R$ por unidade"), width="stretch")

c1, c2 = st.columns(2)
with c1:
    secao("Preço médio por combustível")
    pc = df.groupby("combustivel", observed=True)["preco_medio"].mean().sort_values()
    fig = go.Figure(go.Bar(
        x=pc.values, y=pc.index.astype(str), orientation="h",
        marker=dict(color=[CORES_COMBUSTIVEL[c] for c in pc.index], cornerradius=4),
        text=[fmt_brl(v) for v in pc.values], textposition="outside",
        hovertemplate="%{y}: R$ %{x:.3f}<extra></extra>"))
    fig.update_xaxes(range=[pc.min() * .9, pc.max() * 1.04])
    st.plotly_chart(layout_grafico(fig, 300, legenda=False), width="stretch")
with c2:
    secao("Preço médio por região")
    pr = df.groupby("regiao", observed=True)["preco_medio"].mean().sort_values()
    fig = go.Figure(go.Bar(
        x=pr.values, y=pr.index.astype(str), orientation="h",
        marker=dict(color=[COR_DESTAQUE if r == pr.idxmax() else COR_PRINCIPAL for r in pr.index],
                    cornerradius=4),
        text=[fmt_brl(v) for v in pr.values], textposition="outside",
        hovertemplate="%{y}: R$ %{x:.3f}<extra></extra>"))
    fig.update_xaxes(range=[pr.min() * .9, pr.max() * 1.04])
    st.plotly_chart(layout_grafico(fig, 300, legenda=False), width="stretch")

dif_comb = (pc.max() / pc.min() - 1) * 100
dif_reg = (pr.max() / pr.min() - 1) * 100
interpretacao(
    f"O preço médio no recorte é <b>{fmt_brl(k['preco_medio_nacional'])}</b>. A diferença entre o "
    f"combustível mais caro ({pc.idxmax()}) e o mais barato ({pc.idxmin()}) é de apenas "
    f"<b>{fmt_num(dif_comb, 1)}%</b>, e entre regiões, de <b>{fmt_num(dif_reg, 1)}%</b>. A série "
    f"oscila bastante mês a mês (de {fmt_brl(m['preco_medio'].min())} a "
    f"{fmt_brl(m['preco_medio'].max())}), mas a média móvel permanece praticamente plana: "
    "<b>não há tendência estrutural de alta</b> na base."
)

secao("Conclusão executiva")
interpretacao(
    "<b>1.</b> Os preços giram em torno de R$ 5,50 em todo o período, sem tendência de longo prazo — "
    "as oscilações são de curto prazo e se compensam.<br>"
    "<b>2.</b> Diferenças entre estados, regiões e combustíveis existem, mas são pequenas (poucos %), "
    "menores que a variação de um mês para o outro.<br>"
    "<b>3.</b> Inflação e petróleo <b>não explicam</b> o preço nesta base (correlação ≈ 0), ao contrário "
    "do que ocorre na economia real — veja a página <i>Inflação e petróleo</i>.<br>"
    "<b>4.</b> A base é <b>simulada</b>: os padrões encontrados refletem a geração aleatória dos dados. "
    "A metodologia (tratamento, KPIs, comparações e testes de correlação) é a mesma que se aplicaria "
    "aos dados reais da ANP.",
    titulo="Resumo para decisão",
)
