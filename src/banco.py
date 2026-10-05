"""Persistência em SQLite com modelagem relacional via SQLAlchemy.

Modelo (3ª forma normal):

    regioes 1──N ufs 1──N precos N──1 combustiveis
    indicadores_bcb (série externa do Banco Central, ligada por data)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import (Date, Float, ForeignKey, Integer, String, UniqueConstraint,
                        create_engine, func, select, text)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from src.dados import NOMES_UF, ORDEM_COMBUSTIVEIS, ORDEM_REGIOES, RAIZ

CAMINHO_DB = RAIZ / "database" / "combustiveis.db"

UNIDADES = {"Gasolina": "R$/litro", "Etanol": "R$/litro", "Diesel": "R$/litro",
            "GNV": "R$/m³", "GLP": "R$/kg"}


class Base(DeclarativeBase):
    pass


class Regiao(Base):
    __tablename__ = "regioes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    ufs: Mapped[list["UF"]] = relationship(back_populates="regiao")


class UF(Base):
    __tablename__ = "ufs"
    sigla: Mapped[str] = mapped_column(String(2), primary_key=True)
    nome: Mapped[str] = mapped_column(String(40))
    regiao_id: Mapped[int] = mapped_column(ForeignKey("regioes.id"))
    regiao: Mapped[Regiao] = relationship(back_populates="ufs")


class Combustivel(Base):
    __tablename__ = "combustiveis"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    unidade: Mapped[str] = mapped_column(String(12))


class Preco(Base):
    __tablename__ = "precos"
    __table_args__ = (UniqueConstraint("data", "uf_sigla", "combustivel_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    ano: Mapped[int] = mapped_column(Integer, index=True)
    mes: Mapped[int] = mapped_column(Integer)
    uf_sigla: Mapped[str] = mapped_column(ForeignKey("ufs.sigla"), index=True)
    combustivel_id: Mapped[int] = mapped_column(ForeignKey("combustiveis.id"), index=True)
    preco_medio: Mapped[float] = mapped_column(Float)
    preco_minimo: Mapped[float] = mapped_column(Float)
    preco_maximo: Mapped[float] = mapped_column(Float)
    variacao_mensal: Mapped[float] = mapped_column(Float)
    inflacao: Mapped[float] = mapped_column(Float)
    cotacao_petroleo: Mapped[float] = mapped_column(Float)
    consumo_estimado: Mapped[int] = mapped_column(Integer)
    nivel_preco: Mapped[str] = mapped_column(String(10))


class IndicadorBCB(Base):
    __tablename__ = "indicadores_bcb"
    data: Mapped[date] = mapped_column(Date, primary_key=True)
    ipca_12m: Mapped[float] = mapped_column(Float)


def obter_engine(caminho: Path = CAMINHO_DB) -> Engine:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{caminho.as_posix()}", future=True)


def construir_banco(df: pd.DataFrame, engine: Engine,
                    ipca: pd.DataFrame | None = None) -> None:
    """(Re)cria o esquema e carrega a base tratada nas tabelas normalizadas."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        regioes = {n: Regiao(id=i, nome=n) for i, n in enumerate(ORDEM_REGIOES, 1)}
        s.add_all(regioes.values())
        pares = df[["uf", "regiao"]].astype(str).drop_duplicates()
        s.add_all(UF(sigla=u, nome=NOMES_UF.get(u, u), regiao_id=regioes[r].id)
                  for u, r in pares.itertuples(index=False))
        combs = {n: Combustivel(id=i, nome=n, unidade=UNIDADES[n])
                 for i, n in enumerate(ORDEM_COMBUSTIVEIS, 1)}
        s.add_all(combs.values())
        s.flush()
        registros = [
            dict(data=r.data.date(), ano=int(r.ano), mes=int(r.mes), uf_sigla=r.uf,
                 combustivel_id=combs[str(r.combustivel)].id,
                 preco_medio=r.preco_medio, preco_minimo=r.preco_minimo,
                 preco_maximo=r.preco_maximo, variacao_mensal=r.variacao_mensal,
                 inflacao=r.inflacao, cotacao_petroleo=r.cotacao_petroleo,
                 consumo_estimado=int(r.consumo_estimado), nivel_preco=str(r.nivel_preco))
            for r in df.itertuples(index=False)
        ]
        s.execute(Preco.__table__.insert(), registros)
        if ipca is not None and not ipca.empty:
            s.execute(IndicadorBCB.__table__.insert(), [
                dict(data=d.date(), ipca_12m=float(v))
                for d, v in ipca[["data", "ipca_12m"]].itertuples(index=False)
            ])
        s.commit()


def contar_registros(engine: Engine) -> dict:
    with Session(engine) as s:
        return {t.__tablename__: s.scalar(select(func.count()).select_from(t))
                for t in (Regiao, UF, Combustivel, Preco, IndicadorBCB)}


# Consultas SQL exibidas no dashboard (página Dados & SQL) e no notebook.
CONSULTAS = {
    "Ranking de estados por preço médio": """
        SELECT u.sigla AS uf, u.nome AS estado, r.nome AS regiao,
               ROUND(AVG(p.preco_medio), 3) AS preco_medio,
               COUNT(*) AS registros
        FROM precos p
        JOIN ufs u      ON u.sigla = p.uf_sigla
        JOIN regioes r  ON r.id = u.regiao_id
        GROUP BY u.sigla
        ORDER BY preco_medio DESC""",
    "Preço médio por combustível e unidade": """
        SELECT c.nome AS combustivel, c.unidade,
               ROUND(AVG(p.preco_medio), 3) AS preco_medio,
               ROUND(MIN(p.preco_minimo), 2) AS menor_preco,
               ROUND(MAX(p.preco_maximo), 2) AS maior_preco
        FROM precos p
        JOIN combustiveis c ON c.id = p.combustivel_id
        GROUP BY c.nome
        ORDER BY preco_medio DESC""",
    "Evolução anual por região": """
        SELECT p.ano, r.nome AS regiao, ROUND(AVG(p.preco_medio), 3) AS preco_medio
        FROM precos p
        JOIN ufs u     ON u.sigla = p.uf_sigla
        JOIN regioes r ON r.id = u.regiao_id
        GROUP BY p.ano, r.nome
        ORDER BY p.ano, r.nome""",
    "Meses mais instáveis (desvio da variação mensal)": """
        WITH m AS (
            SELECT data, AVG(variacao_mensal) AS media,
                   AVG(variacao_mensal * variacao_mensal) AS media_quad
            FROM precos GROUP BY data)
        SELECT data, ROUND(media, 2) AS variacao_media,
               ROUND(SQRT(media_quad - media * media), 2) AS volatilidade
        FROM m ORDER BY volatilidade DESC LIMIT 12""",
    "Preço simulado x IPCA real do Banco Central": """
        SELECT p.data, ROUND(AVG(p.preco_medio), 3) AS preco_medio,
               ROUND(AVG(p.inflacao), 2) AS inflacao_simulada,
               b.ipca_12m AS ipca_real_12m
        FROM precos p
        LEFT JOIN indicadores_bcb b ON b.data = p.data
        GROUP BY p.data
        ORDER BY p.data""",
}


def executar_consulta(engine: Engine, sql: str) -> pd.DataFrame:
    with engine.connect() as con:
        return pd.read_sql(text(sql), con)
