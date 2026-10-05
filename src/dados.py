from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_CSV = RAIZ / "dados" / "simulacao_precos_combustiveis_brasil.csv"
CAMINHO_GEOJSON = RAIZ / "dados" / "brasil_estados.geojson"

COLUNAS_ESPERADAS = [
    "ano", "mes", "data", "regiao", "uf", "combustivel", "preco_medio",
    "preco_minimo", "preco_maximo", "variacao_mensal", "inflacao",
    "cotacao_petroleo", "consumo_estimado", "nivel_preco",
]
CHAVE = ["data", "uf", "combustivel"]

NOMES_UF = {
    "AM": "Amazonas", "PA": "Pará", "RO": "Rondônia", "TO": "Tocantins",
    "BA": "Bahia", "PE": "Pernambuco", "CE": "Ceará", "MA": "Maranhão",
    "PB": "Paraíba", "DF": "Distrito Federal", "GO": "Goiás",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "SP": "São Paulo",
    "RJ": "Rio de Janeiro", "MG": "Minas Gerais", "ES": "Espírito Santo",
    "PR": "Paraná", "SC": "Santa Catarina", "RS": "Rio Grande do Sul",
}
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ORDEM_COMBUSTIVEIS = ["Gasolina", "Etanol", "Diesel", "GNV", "GLP"]
ORDEM_NIVEIS = ["Baixo", "Médio", "Alto", "Crítico"]
NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def carregar_bruto(origem=CAMINHO_CSV) -> pd.DataFrame:
    return pd.read_csv(origem, encoding="utf-8-sig")


def validar_colunas(df: pd.DataFrame) -> list[str]:
    return [c for c in COLUNAS_ESPERADAS if c not in df.columns]


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["regiao", "uf", "combustivel", "nivel_preco"]:
        df[col] = df[col].astype(str).str.strip()
    df["uf"] = df["uf"].str.upper()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data", "preco_medio"])

    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month

    precos = np.sort(df[["preco_minimo", "preco_medio", "preco_maximo"]].to_numpy(), axis=1)
    df[["preco_minimo", "preco_medio", "preco_maximo"]] = precos

    numericas = ["preco_medio", "preco_minimo", "preco_maximo", "variacao_mensal",
                 "inflacao", "cotacao_petroleo", "consumo_estimado"]
    agg = {c: "mean" for c in numericas}
    agg.update({
        "regiao": "first", "ano": "first", "mes": "first",
        "nivel_preco": lambda s: s.mode().iat[0],
    })
    df = df.groupby(CHAVE, as_index=False).agg(agg)
    df[["preco_medio", "preco_minimo", "preco_maximo"]] = (
        df[["preco_medio", "preco_minimo", "preco_maximo"]].round(2)
    )
    df["consumo_estimado"] = df["consumo_estimado"].round().astype("int64")
    return df.sort_values(CHAVE).reset_index(drop=True)


def criar_atributos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["nome_uf"] = df["uf"].map(NOMES_UF).fillna(df["uf"])
    df["trimestre"] = df["data"].dt.quarter
    df["semestre"] = np.where(df["mes"] <= 6, 1, 2)
    df["nome_mes"] = pd.Categorical(
        df["mes"].map(lambda m: NOMES_MESES[m - 1]), NOMES_MESES, ordered=True
    )
    df["periodo"] = df["data"].dt.strftime("%Y-%m")
    df["amplitude"] = (df["preco_maximo"] - df["preco_minimo"]).round(2)
    df["amplitude_pct"] = (df["amplitude"] / df["preco_medio"] * 100).round(2)
    df["direcao"] = np.select(
        [df["variacao_mensal"] > 0, df["variacao_mensal"] < 0],
        ["Alta", "Queda"], "Estável",
    )
    df["variacao_abs"] = df["variacao_mensal"].abs()
    df["faixa_preco"] = df.groupby("combustivel")["preco_medio"].transform(
        lambda s: pd.qcut(s, 4, labels=ORDEM_NIVEIS)
    ).astype(str)
    df["zscore_preco"] = df.groupby("combustivel")["preco_medio"].transform(
        lambda s: (s - s.mean()) / s.std()
    ).round(3)
    df["regiao"] = pd.Categorical(df["regiao"], ORDEM_REGIOES, ordered=True)
    df["combustivel"] = pd.Categorical(df["combustivel"], ORDEM_COMBUSTIVEIS, ordered=True)
    df["nivel_preco"] = pd.Categorical(df["nivel_preco"], ORDEM_NIVEIS, ordered=True)
    return df


def preparar(origem=CAMINHO_CSV) -> pd.DataFrame:
    return criar_atributos(limpar(carregar_bruto(origem)))


def indicadores_mensais(df: pd.DataFrame) -> pd.DataFrame:
    m = df.groupby("data", observed=True).agg(
        preco_medio=("preco_medio", "mean"),
        inflacao=("inflacao", "mean"),
        cotacao_petroleo=("cotacao_petroleo", "mean"),
        variacao_media=("variacao_mensal", "mean"),
        volatilidade=("variacao_mensal", "std"),
        pct_critico=("nivel_preco", lambda s: (s == "Crítico").mean() * 100),
        consumo=("consumo_estimado", "sum"),
    ).reset_index()
    m["media_movel_12m"] = m["preco_medio"].rolling(12, min_periods=3).mean()
    return m


def volatilidade_por(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    g = df.groupby(coluna, observed=True)
    out = pd.DataFrame({
        "preco_medio": g["preco_medio"].mean(),
        "desvio_preco": g["preco_medio"].std(),
        "desvio_variacao": g["variacao_mensal"].std(),
        "maior_alta": g["variacao_mensal"].max(),
        "maior_queda": g["variacao_mensal"].min(),
        "registros": g.size(),
    })
    out["cv_pct"] = out["desvio_preco"] / out["preco_medio"] * 100
    return out.round(3).reset_index()


def aumento_periodo(df: pd.DataFrame, coluna: str = "combustivel") -> pd.DataFrame:
    anos = sorted(df["ano"].unique())
    if len(anos) < 2:
        return pd.DataFrame(columns=[coluna, "inicio", "fim", "aumento_pct"])
    t = df[df["ano"].isin([anos[0], anos[-1]])].pivot_table(
        index=coluna, columns="ano", values="preco_medio", aggfunc="mean", observed=True
    )
    out = pd.DataFrame({
        "inicio": t[anos[0]], "fim": t[anos[-1]],
        "aumento_pct": (t[anos[-1]] / t[anos[0]] - 1) * 100,
    }).round(3).reset_index()
    return out.sort_values("aumento_pct", ascending=False)


def kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    por_comb = df.groupby("combustivel", observed=True)["preco_medio"].mean()
    por_uf = df.groupby("uf")["preco_medio"].mean()
    por_reg = df.groupby("regiao", observed=True)["preco_medio"].mean()
    linha_var = df.loc[df["variacao_abs"].idxmax()]
    return {
        "preco_medio_nacional": df["preco_medio"].mean(),
        "combustivel_mais_caro": por_comb.idxmax(),
        "combustivel_mais_caro_preco": por_comb.max(),
        "uf_mais_cara": por_uf.idxmax(),
        "uf_mais_cara_preco": por_uf.max(),
        "maior_variacao": linha_var["variacao_mensal"],
        "maior_variacao_desc": f"{linha_var['combustivel']} · {linha_var['uf']} · "
                               f"{linha_var['data']:%m/%Y}",
        "consumo_total": df["consumo_estimado"].sum(),
        "regiao_mais_cara": por_reg.idxmax(),
        "regiao_mais_cara_preco": por_reg.max(),
    }


def fmt_brl(valor: float, casas: int = 2) -> str:
    s = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_num(valor: float, casas: int = 0) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_compacto(valor: float) -> str:
    for limite, sufixo in [(1e9, " bi"), (1e6, " mi"), (1e3, " mil")]:
        if abs(valor) >= limite:
            return fmt_num(valor / limite, 1) + sufixo
    return fmt_num(valor)
