"""Frequência de eventos (releases, tags, deployments) por semana."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd


def _para_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _data_para_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def frequencia(
    df: pd.DataFrame,
    inicio: date,
    fim: date,
    coluna_data: str = "publicada_em",
    periodo: str | None = None,
) -> "float | pd.Series":
    """Frequência de eventos na janela [inicio, fim], em eventos/semana.

    Com periodo='Q', retorna Series com índice Period (trimestre) e
    contagem total por trimestre (não por semana).
    """
    if df.empty or coluna_data not in df.columns:
        if periodo:
            return pd.Series(dtype=float)
        return 0.0

    inicio_dt = _data_para_utc(inicio)
    fim_dt = datetime(fim.year, fim.month, fim.day, 23, 59, 59, tzinfo=timezone.utc)

    datas = df[coluna_data].apply(_para_utc)
    mask = (datas >= inicio_dt) & (datas <= fim_dt)
    filtrado = datas[mask]

    if periodo == "Q":
        return filtrado.dt.to_period("Q").value_counts().sort_index()

    semanas = (fim_dt - inicio_dt).total_seconds() / (7 * 24 * 3600)
    return len(filtrado) / semanas if semanas > 0 else 0.0
