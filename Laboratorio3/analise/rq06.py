"""RQ 06: fatores associados ao desempenho DORA."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def quartis_labels(serie: pd.Series) -> pd.Series:
    """Divide série numérica em 4 quartis rotulados Q1..Q4 (Q1 = menor).

    duplicates='drop' evita erro quando muitos valores são idênticos.
    """
    return pd.qcut(serie, q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")


def mapear_linguagem(serie: pd.Series, top_n: int = 7) -> pd.Series:
    """Mantém as top_n linguagens mais frequentes; as demais viram 'Outras'."""
    top = serie.value_counts().head(top_n).index
    return serie.where(serie.isin(top), other="Outras")


def testar_kruskal(grupos: dict[str, pd.Series]) -> dict:
    """Kruskal-Wallis para múltiplos grupos; retorna H, pvalue, ε², n_total, n_por_grupo."""
    amostras = [v.dropna().values for v in grupos.values()]
    H, p = stats.kruskal(*amostras)
    n_total = sum(len(a) for a in amostras)
    epsilon2 = H / (n_total - 1) if n_total > 1 else float("nan")
    return {
        "teste": "kruskal",
        "H": float(H),
        "pvalue": float(p),
        "epsilon2": float(epsilon2),
        "n_total": n_total,
        "n_por_grupo": {k: len(v.dropna()) for k, v in grupos.items()},
    }


def testar_mann_whitney(x: pd.Series, y: pd.Series) -> dict:
    """Mann-Whitney U e Cliff's delta entre dois grupos."""
    a, b = x.dropna().values, y.dropna().values
    n1, n2 = len(a), len(b)
    result = stats.mannwhitneyu(a, b, alternative="two-sided")
    U1 = float(result.statistic)
    cliff_delta = 2 * U1 / (n1 * n2) - 1 if n1 * n2 > 0 else float("nan")
    return {
        "teste": "mann_whitney",
        "U": U1,
        "pvalue": float(result.pvalue),
        "cliff_delta": float(cliff_delta),
        "n1": n1,
        "n2": n2,
        "n_total": n1 + n2,
    }


def testar_fator_metrica(df: pd.DataFrame, fator_col: str, metrica_col: str) -> dict:
    """Testa associação fator × métrica; escolhe Kruskal ou Mann-Whitney pelo nº de grupos.

    Descarta NaN tanto no fator quanto na métrica antes de agrupar.
    """
    sub = df[[fator_col, metrica_col]].dropna(subset=[fator_col, metrica_col])
    grupos = {
        str(g): sub.loc[sub[fator_col] == g, metrica_col]
        for g in sub[fator_col].unique()
    }
    grupos = {k: v for k, v in grupos.items() if len(v) >= 2}
    n_grupos = len(grupos)
    resultado = {"fator": fator_col, "metrica": metrica_col}
    if n_grupos < 2:
        resultado.update({"teste": "skip", "pvalue": float("nan"), "n_total": 0})
    elif n_grupos == 2:
        k1, k2 = list(grupos.keys())
        resultado.update(testar_mann_whitney(grupos[k1], grupos[k2]))
    else:
        resultado.update(testar_kruskal(grupos))
    return resultado
