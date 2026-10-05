"""Consumo da API de Séries Temporais (SGS) do Banco Central do Brasil.

Série 13522 — IPCA acumulado em 12 meses (%). Serve de referência real para
comparar com a coluna `inflacao` da base simulada. Se a API estiver fora do
ar, usamos a cópia local salva em dados/ipca_bcb_12m.csv.
"""
from __future__ import annotations

import pandas as pd
import requests

from src.dados import RAIZ

SERIE_IPCA_12M = 13522
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
CAMINHO_CACHE = RAIZ / "dados" / "ipca_bcb_12m.csv"


def buscar_ipca_api(inicio: str = "01/01/2015", fim: str = "31/12/2024",
                    timeout: int = 10) -> pd.DataFrame:
    resp = requests.get(
        URL_SGS.format(serie=SERIE_IPCA_12M),
        params={"formato": "json", "dataInicial": inicio, "dataFinal": fim},
        timeout=timeout,
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["ipca_12m"] = pd.to_numeric(df["valor"])
    return df[["data", "ipca_12m"]]


def obter_ipca() -> tuple[pd.DataFrame, str]:
    """Retorna (série, origem). Atualiza o cache local quando a API responde."""
    try:
        df = buscar_ipca_api()
        df.to_csv(CAMINHO_CACHE, index=False)
        return df, "API do Banco Central (ao vivo)"
    except (requests.RequestException, ValueError, KeyError):
        if CAMINHO_CACHE.exists():
            return pd.read_csv(CAMINHO_CACHE, parse_dates=["data"]), "cópia local (API indisponível)"
        return pd.DataFrame(columns=["data", "ipca_12m"]), "indisponível"
