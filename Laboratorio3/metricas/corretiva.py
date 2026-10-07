"""Heurística v0 de release corretiva; CFR(b), recuperação e rework rate."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

import pandas as pd

_SEMVER_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)(?:[.\-+][a-zA-Z0-9._+-]*)?$"
)
_CORRETIVO_RE = re.compile(r"\b(fix|hotfix|revert)\b", re.IGNORECASE)


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    """Retorna (major, minor, patch) ou None se não for SemVer."""
    m = _SEMVER_RE.match(tag.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def eh_corretiva(
    tag_anterior: str,
    tag_atual: str,
    commits_intervalo: pd.DataFrame,
) -> bool:
    """True se a release é corretiva: só o patch mudou OU há commit fix/hotfix/revert."""
    sv_ant = parse_semver(tag_anterior)
    sv_atu = parse_semver(tag_atual)
    so_patch = (
        sv_ant is not None
        and sv_atu is not None
        and sv_ant[0] == sv_atu[0]
        and sv_ant[1] == sv_atu[1]
        and sv_atu[2] > sv_ant[2]
    )
    tem_commit_fix = (
        not commits_intervalo.empty
        and commits_intervalo["mensagem"].apply(
            lambda m: bool(_CORRETIVO_RE.search(str(m)))
        ).any()
    )
    return bool(so_patch or tem_commit_fix)


def _para_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _dias_entre(pub_ant: str, pub_atu: str) -> float:
    return (_para_utc(pub_atu) - _para_utc(pub_ant)).total_seconds() / 86400


def cfr_releases(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    janela_fim: date,
    janela_dias: int = 7,
) -> float:
    """CFR(b): releases que falharam ÷ releases avaliadas.

    Releases nos últimos `janela_dias` dias da janela são censuradas.
    """
    na_janela = releases_df[releases_df["na_janela"]].sort_values("publicada_em")
    todas = releases_df.sort_values("publicada_em")
    fim_dt = datetime(janela_fim.year, janela_fim.month, janela_fim.day,
                      23, 59, 59, tzinfo=timezone.utc)

    avaliadas = 0
    falhas = 0

    for _, rel in na_janela.iterrows():
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            continue

        pub_dt = _para_utc(rel["publicada_em"])
        dias_ate_fim = (fim_dt - pub_dt).total_seconds() / 86400
        if dias_ate_fim < janela_dias:
            continue  # censurada

        avaliadas += 1
        posteriores = na_janela[na_janela["publicada_em"] > rel["publicada_em"]]
        for _, prox in posteriores.iterrows():
            if _dias_entre(rel["publicada_em"], prox["publicada_em"]) > janela_dias:
                break
            commits_prox = (commits_df[commits_df["release_tag"] == prox["tag"]]
                            if not commits_df.empty else pd.DataFrame())
            if eh_corretiva(rel["tag"], prox["tag"], commits_prox):
                falhas += 1
                break

    if avaliadas == 0:
        return float("nan")
    return falhas / avaliadas


def recuperacao_releases(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    janela_fim: date,
    janela_dias: int = 7,
) -> pd.Series:
    """Horas entre cada release que falhou e a respectiva corretiva."""
    na_janela = releases_df[releases_df["na_janela"]].sort_values("publicada_em")
    todas = releases_df.sort_values("publicada_em")
    fim_dt = datetime(janela_fim.year, janela_fim.month, janela_fim.day,
                      23, 59, 59, tzinfo=timezone.utc)

    horas: list[float] = []

    for _, rel in na_janela.iterrows():
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            continue
        pub_dt = _para_utc(rel["publicada_em"])
        dias_ate_fim = (fim_dt - pub_dt).total_seconds() / 86400
        if dias_ate_fim < janela_dias:
            continue

        posteriores = na_janela[na_janela["publicada_em"] > rel["publicada_em"]]
        for _, prox in posteriores.iterrows():
            if _dias_entre(rel["publicada_em"], prox["publicada_em"]) > janela_dias:
                break
            commits_prox = (commits_df[commits_df["release_tag"] == prox["tag"]]
                            if not commits_df.empty else pd.DataFrame())
            if eh_corretiva(rel["tag"], prox["tag"], commits_prox):
                h = (_para_utc(prox["publicada_em"]) - pub_dt).total_seconds() / 3600
                horas.append(h)
                break

    return pd.Series(horas)


def rework_rate(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    limite_dias: int | None = None,
) -> float:
    """Proporção de releases corretivas sobre total avaliadas.

    Exclui a primeira release da história (sem anterior).
    Com limite_dias: conta só corretivas publicadas dentro de limite_dias da anterior.
    """
    todas = releases_df[releases_df["na_janela"]].sort_values("publicada_em")
    avaliadas = 0
    corretivas = 0

    for _, rel in todas.iterrows():
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            continue  # primeira da história

        avaliadas += 1
        ant = anteriores.sort_values("publicada_em").iloc[-1]

        if limite_dias is not None:
            if _dias_entre(ant["publicada_em"], rel["publicada_em"]) > limite_dias:
                continue

        commits_rel = (commits_df[commits_df["release_tag"] == rel["tag"]]
                       if not commits_df.empty else pd.DataFrame())
        if eh_corretiva(ant["tag"], rel["tag"], commits_rel):
            corretivas += 1

    if avaliadas == 0:
        return float("nan")
    return corretivas / avaliadas
