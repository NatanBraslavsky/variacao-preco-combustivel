import streamlit as st

from src.dados import (aumento_periodo, fmt_brl, fmt_num, indicadores_mensais, volatilidade_por)
from src.ui import cabecalho, interpretacao, secao, sem_dados

df = st.session_state["df"]
cabecalho("Conclusão executiva", "Respostas às perguntas orientadoras",
          "Síntese dos achados para o recorte atual. Os números se atualizam com os filtros.")
if df.empty or df["ano"].nunique() < 2:
    sem_dados() if df.empty else st.info("Selecione pelo menos dois anos para gerar as conclusões.")
    st.stop()

por_uf = df.groupby("nome_uf")["preco_medio"].mean().sort_values(ascending=False)
por_reg = df.groupby("regiao", observed=True)["preco_medio"].agg(["mean", "std"])
aum = aumento_periodo(df)
vol = volatilidade_por(df, "combustivel").sort_values("desvio_variacao", ascending=False)
m = indicadores_mensais(df)
anual = df.groupby("ano")["preco_medio"].mean()
r_inf = df["inflacao"].corr(df["preco_medio"])
r_pet = df["cotacao_petroleo"].corr(df["preco_medio"])
pico = m.loc[m["volatilidade"].idxmax()]

respostas = [
    ("Quais estados possuem combustíveis mais caros?",
     f"{', '.join(por_uf.index[:3])} lideram, com média de {fmt_brl(por_uf.iloc[0])} no topo. "
     f"O mais barato é {por_uf.index[-1]} ({fmt_brl(por_uf.iloc[-1])}). Diferença total de "
     f"{fmt_num((por_uf.iloc[0] / por_uf.iloc[-1] - 1) * 100, 1)}%."),
    ("Qual combustível apresentou maior aumento?",
     f"{aum.iloc[0]['combustivel']}, com {fmt_num(aum.iloc[0]['aumento_pct'], 1)}% entre o primeiro e o "
     f"último ano. {aum.iloc[-1]['combustivel']} teve o menor resultado "
     f"({fmt_num(aum.iloc[-1]['aumento_pct'], 1)}%)."),
    ("Existem diferenças regionais relevantes?",
     f"Pouco. {por_reg['mean'].idxmax()} é a mais cara e {por_reg['mean'].idxmin()} a mais barata, mas a "
     f"diferença ({fmt_brl(por_reg['mean'].max() - por_reg['mean'].min())}) é bem menor que o desvio "
     f"interno de cada região (≈ {fmt_brl(por_reg['std'].mean())})."),
    ("Há períodos de maior instabilidade?",
     f"Sim, em meses isolados — o pico foi {pico['data']:%m/%Y} ({fmt_num(pico['volatilidade'], 2)} p.p.). "
     "Mas eles se espalham pelos anos sem formar crises prolongadas."),
    ("Como os preços evoluíram ao longo do tempo?",
     f"De forma estável: a média anual fica entre {fmt_brl(anual.min())} e {fmt_brl(anual.max())}. "
     "Há muita oscilação mensal, porém sem tendência de alta ou queda."),
    ("Existe relação entre inflação e combustíveis?",
     f"Não nesta base: r = {fmt_num(r_inf, 3)} com a inflação e r = {fmt_num(r_pet, 3)} com o petróleo, "
     "estatisticamente indistinguíveis de zero."),
    ("Quais combustíveis possuem maior volatilidade?",
     f"{vol.iloc[0]['combustivel']} ({fmt_num(vol.iloc[0]['desvio_variacao'], 2)} p.p.), seguido de "
     f"{vol.iloc[1]['combustivel']}. A diferença para o mais estável ({vol.iloc[-1]['combustivel']}) "
     "é pequena — todos oscilam de forma parecida." if len(vol) > 1 else
     f"Apenas {vol.iloc[0]['combustivel']} está selecionado (desvio de "
     f"{fmt_num(vol.iloc[0]['desvio_variacao'], 2)} p.p.). Selecione mais combustíveis para comparar."),
]
if aum["combustivel"].nunique() < 2:
    respostas[1] = (respostas[1][0],
                    f"Com um único combustível selecionado, a variação no período foi de "
                    f"{fmt_num(aum.iloc[0]['aumento_pct'], 1)}%. Selecione mais combustíveis para comparar.")
if len(por_reg) < 2:
    respostas[2] = (respostas[2][0], "Selecione mais de uma região para comparar.")

secao("As 7 perguntas do projeto")
c1, c2 = st.columns(2)
for i, (pergunta, resposta) in enumerate(respostas):
    with (c1 if i % 2 == 0 else c2):
        interpretacao(resposta, titulo=f"{i + 1}. {pergunta}")

secao("Interpretação econômica")
interpretacao(
    "Na economia real, combustíveis acompanham o petróleo (via política de preços da Petrobras), "
    "o câmbio e a carga tributária (ICMS estadual), o que gera diferenças regionais persistentes e "
    "picos como o de 2021–2022. <b>A base analisada não reproduz esses mecanismos</b>: preços, "
    "inflação e petróleo foram gerados de forma independente. Por isso, a principal conclusão "
    "analítica é <b>a ausência de padrão</b> — e reconhecê-la evita tirar conclusões falsas de "
    "rankings que mudam a cada filtro."
)

secao("Limitações e próximos passos")
interpretacao(
    "<b>Limitações:</b> dados simulados; registros duplicados consolidados (4.440 → 3.937); "
    "coluna <code>nivel_preco</code> sem relação com o preço (foi criada a <i>faixa recalculada</i> por "
    "quartis); amostragem desigual entre estados; todos os combustíveis na mesma escala de preço "
    "(no real, GLP é vendido por botijão de 13 kg).<br>"
    "<b>Próximos passos:</b> aplicar o mesmo pipeline aos dados abertos da ANP (Levantamento de "
    "Preços de Combustíveis), incluir câmbio e ICMS como variáveis explicativas e testar modelos de "
    "séries temporais (sazonalidade, defasagem petróleo → bomba).",
    titulo="Transparência", aviso=True,
)
