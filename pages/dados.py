import pandas as pd
import streamlit as st

from src.banco import CONSULTAS, contar_registros, executar_consulta
from src.dados import COLUNAS_ESPERADAS, criar_atributos, limpar, validar_colunas
from src.ui import cabecalho, interpretacao, secao, sem_dados

df = st.session_state["df"]
engine = st.session_state["engine"]
cabecalho("Exploração detalhada", "Dados, tabela dinâmica e SQL",
          "Monte sua própria tabela dinâmica, consulte o banco SQLite via SQLAlchemy, "
          "baixe o recorte filtrado ou envie outra base no mesmo formato.")

aba_pivot, aba_sql, aba_dados, aba_upload = st.tabs(
    ["Tabela dinâmica", "Consultas SQL", "Registros", "Enviar CSV"])

# ------------------------------------------------------------ tabela dinâmica
with aba_pivot:
    if df.empty:
        sem_dados()
    else:
        dims = {"Ano": "ano", "Mês": "nome_mes", "Trimestre": "trimestre", "Região": "regiao",
                "UF": "uf", "Combustível": "combustivel", "Nível de preço": "nivel_preco",
                "Faixa recalculada": "faixa_preco", "Direção": "direcao"}
        metricas = {"Preço médio": "preco_medio", "Preço mínimo": "preco_minimo",
                    "Preço máximo": "preco_maximo", "Variação mensal": "variacao_mensal",
                    "Consumo estimado": "consumo_estimado", "Amplitude": "amplitude",
                    "Inflação": "inflacao", "Petróleo": "cotacao_petroleo"}
        aggs = {"Média": "mean", "Mediana": "median", "Soma": "sum", "Mínimo": "min",
                "Máximo": "max", "Desvio padrão": "std", "Contagem": "count"}
        c1, c2, c3, c4 = st.columns(4)
        linhas = c1.selectbox("Linhas", list(dims), index=3)
        colunas = c2.selectbox("Colunas", ["(nenhuma)"] + list(dims), index=6)
        valor = c3.selectbox("Valor", list(metricas))
        agg = c4.selectbox("Agregação", list(aggs))
        if colunas == linhas:
            st.warning("Escolha dimensões diferentes para linhas e colunas.")
        else:
            pivot = df.pivot_table(
                index=dims[linhas], columns=None if colunas == "(nenhuma)" else dims[colunas],
                values=metricas[valor], aggfunc=aggs[agg], observed=True, margins=True,
                margins_name="Total")
            if isinstance(pivot, pd.Series):
                pivot = pivot.to_frame(valor)
            pivot.columns = [str(c) for c in pivot.columns]
            st.dataframe(pivot.style.format(precision=2, decimal=",", thousands=".")
                         .background_gradient(cmap="Blues", axis=None,
                                              subset=pd.IndexSlice[pivot.index[:-1], pivot.columns[:-1]]
                                              if pivot.shape[1] > 1 else None),
                         width="stretch")
            st.download_button("Baixar tabela dinâmica (CSV)", pivot.to_csv(sep=";", decimal=","),
                               "tabela_dinamica.csv", "text/csv", icon=":material/download:")

# ------------------------------------------------------------ SQL
with aba_sql:
    st.caption("Consultas executadas diretamente no banco `database/combustiveis.db` "
               "(base completa, sem os filtros da barra lateral).")
    cont = contar_registros(engine)
    st.markdown(" · ".join(f"`{t}`: **{n}**" for t, n in cont.items()))
    nome = st.selectbox("Consulta", list(CONSULTAS))
    with st.expander("Ver SQL", icon=":material/code:"):
        st.code(CONSULTAS[nome].strip(), language="sql")
    resultado = executar_consulta(engine, CONSULTAS[nome])
    st.dataframe(resultado, hide_index=True, width="stretch")
    interpretacao(
        "O banco segue um <b>modelo relacional normalizado</b>: <code>regioes</code> 1–N "
        "<code>ufs</code> 1–N <code>precos</code> N–1 <code>combustiveis</code>, mais a tabela "
        "<code>indicadores_bcb</code> com o IPCA real da API do Banco Central, ligada por data. "
        "As consultas usam JOINs, agregações e CTE.",
        titulo="Modelagem relacional",
    )

# ------------------------------------------------------------ registros
with aba_dados:
    if df.empty:
        sem_dados()
    else:
        colunas_vis = ["periodo", "regiao", "uf", "combustivel", "preco_medio", "preco_minimo",
                       "preco_maximo", "amplitude", "variacao_mensal", "inflacao",
                       "cotacao_petroleo", "consumo_estimado", "nivel_preco", "faixa_preco"]
        st.dataframe(df[colunas_vis], hide_index=True, width="stretch", height=460)
        st.download_button("Baixar recorte filtrado (CSV)",
                           df[colunas_vis].to_csv(index=False).encode("utf-8-sig"),
                           "combustiveis_filtrado.csv", "text/csv", icon=":material/download:")

# ------------------------------------------------------------ upload
with aba_upload:
    st.markdown("Envie um CSV com as mesmas 14 colunas da base original para analisá-lo em todo "
                "o painel. O arquivo passa pelo mesmo tratamento (limpeza + atributos).")
    st.caption("Colunas: " + ", ".join(f"`{c}`" for c in COLUNAS_ESPERADAS))
    arquivo = st.file_uploader("Arquivo CSV", type="csv")
    if arquivo is not None and st.session_state.get("nome_upload") != arquivo.name:
        try:
            bruto = pd.read_csv(arquivo, encoding="utf-8-sig", sep=None, engine="python")
            faltando = validar_colunas(bruto)
            if faltando:
                st.error("Colunas ausentes: " + ", ".join(faltando) + ". Corrija o arquivo e envie de novo.")
            else:
                st.session_state["df_upload"] = criar_atributos(limpar(bruto))
                st.session_state["nome_upload"] = arquivo.name
                st.rerun()
        except Exception as erro:  # arquivo corrompido, encoding etc.
            st.error(f"Não foi possível ler o arquivo: {erro}")
    if "df_upload" in st.session_state:
        st.success(f"Usando a base enviada: **{st.session_state['nome_upload']}** "
                   f"({len(st.session_state['df_upload'])} registros após o tratamento).")
        if st.button("Voltar para a base original", icon=":material/restart_alt:"):
            for chave in ("df_upload", "nome_upload"):
                st.session_state.pop(chave, None)
            st.rerun()
