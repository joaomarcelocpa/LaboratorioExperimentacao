"""RQ 05: correlação de Spearman entre frequência de deploy e CFR."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats


def correlacao_spearman(x: pd.Series, y: pd.Series) -> dict:
    """Correlação de Spearman entre x e y, descartando pares com NaN.

    Retorna dict com 'rho', 'pvalue', 'n'.
    """
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(df)
    if n < 3:
        return {"rho": float("nan"), "pvalue": float("nan"), "n": n}
    result = stats.spearmanr(df["x"], df["y"])
    return {"rho": float(result.statistic), "pvalue": float(result.pvalue), "n": n}
