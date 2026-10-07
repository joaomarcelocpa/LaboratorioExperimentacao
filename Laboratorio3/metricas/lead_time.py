"""Lead time for changes: tempo entre commit e respectiva release."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def _para_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def lead_time_por_release(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
) -> pd.Series:
    """Para cada release na janela com release anterior, calcula
    publicada_em - min(commits.data_autor), em horas.

    Retorna Series com índice=tag, valores em horas (NaN se sem commits).
    Releases sem release anterior não entram no índice.
    """
    na_janela = releases_df[releases_df["na_janela"]].copy()
    todas = releases_df.sort_values("publicada_em")

    resultados: dict[str, float] = {}
    for _, rel in na_janela.iterrows():
        tag = rel["tag"]
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            continue  # primeira release da história → não entra
        rel_commits = commits_df[commits_df["release_tag"] == tag] if not commits_df.empty else pd.DataFrame()
        if rel_commits.empty:
            resultados[tag] = float("nan")
            continue
        pub = _para_utc(rel["publicada_em"])
        mais_antigo = rel_commits["data_autor"].apply(_para_utc).min()
        resultados[tag] = (pub - mais_antigo).total_seconds() / 3600

    return pd.Series(resultados)


def lead_time_por_commit(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    excluir_bots: bool = False,
    periodo: str | None = None,
) -> "float | pd.Series":
    """Mediana de (publicada_em - data_autor) em horas para todos os commits
    de todas as releases na janela que têm release anterior.

    Com periodo='Q' retorna Series com mediana por trimestre.
    """
    na_janela = releases_df[releases_df["na_janela"]].copy()
    todas = releases_df.sort_values("publicada_em")

    lead_times: list[float] = []
    periodos: list = []

    for _, rel in na_janela.iterrows():
        tag = rel["tag"]
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            continue

        rel_commits = (commits_df[commits_df["release_tag"] == tag].copy()
                       if not commits_df.empty else pd.DataFrame())
        if excluir_bots and not rel_commits.empty:
            rel_commits = rel_commits[~rel_commits["eh_bot"]]
        if rel_commits.empty:
            continue

        pub = _para_utc(rel["publicada_em"])
        for _, c in rel_commits.iterrows():
            lt = (pub - _para_utc(c["data_autor"])).total_seconds() / 3600
            lead_times.append(lt)
            if periodo == "Q":
                periodos.append(pd.Period(rel["publicada_em"][:7], "Q"))

    if not lead_times:
        if periodo == "Q":
            return pd.Series(dtype=float)
        return float("nan")

    s = pd.Series(lead_times)
    if periodo == "Q":
        s.index = pd.PeriodIndex(periodos)
        return s.groupby(level=0).median()

    return float(s.median())


def pct_commits_bot(commits_df: pd.DataFrame) -> float:
    """Proporção de commits feitos por bots. NaN se sem commits."""
    if commits_df.empty or "eh_bot" not in commits_df.columns:
        return float("nan")
    return float(commits_df["eh_bot"].mean())
