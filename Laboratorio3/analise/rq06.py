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
