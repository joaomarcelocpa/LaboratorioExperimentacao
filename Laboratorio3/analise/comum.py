"""Funções comuns às análises da S03 (RQ 01 a RQ 08).

Cada script de análise lê os CSVs de `data/processed/` por aqui e grava
tabelas em `analise/saida/tabelas/` e figuras em `analise/saida/figuras/`, para que todos usem os mesmos caminhos
e o mesmo formato.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem janela: roda no CI e no Docker

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data" / "processed"
SAIDA = Path(__file__).resolve().parent / "saida"


def _ler(nome: str) -> pd.DataFrame:
    caminho = DADOS / nome
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não existe: rode `make run` antes da análise")
    return pd.read_csv(caminho)


def carregar_metricas() -> pd.DataFrame:
    """metricas.csv: uma linha por repositório."""
    return _ler("metricas.csv")


def carregar_repos() -> pd.DataFrame:
    """repos.csv: fatores do repositório (estrelas, linguagem, idade...)."""
    return _ler("repos.csv")


def carregar_metricas_mensais() -> pd.DataFrame:
    """metricas_mensais.csv: métricas por repositório e mês (RQ 08)."""
    return _ler("metricas_mensais.csv")


def resumo(serie: pd.Series) -> dict:
    """Mediana, IQR e n de uma coluna. Valor ausente fica de fora e o n diz quantos sobraram."""
    dados = serie.dropna()
    if dados.empty:
        return {"n": 0, "mediana": float("nan"), "q1": float("nan"),
                "q3": float("nan"), "iqr": float("nan")}
    q1, q3 = dados.quantile(0.25), dados.quantile(0.75)
    return {"n": int(len(dados)), "mediana": float(dados.median()),
            "q1": float(q1), "q3": float(q3), "iqr": float(q3 - q1)}


def tabela_resumo(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Uma linha por coluna, com n, mediana, q1, q3 e iqr."""
    linhas = {c: resumo(df[c]) for c in colunas}
    return pd.DataFrame.from_dict(linhas, orient="index").rename_axis("metrica")


def salvar_tabela(tabela: pd.DataFrame, nome: str) -> Path:
    """Grava `analise/saida/tabelas/<nome>.csv` e devolve o caminho."""
    pasta = SAIDA / "tabelas"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.csv"
    tabela.to_csv(caminho)
    return caminho


def salvar_figura(fig: plt.Figure, nome: str) -> Path:
    """Grava `analise/saida/figuras/<nome>.png` e fecha a figura."""
    pasta = SAIDA / "figuras"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho
