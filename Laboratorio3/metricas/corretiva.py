"""Heurística de release corretiva (variantes v1-v4); CFR(b), recuperação e rework rate."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Literal

import pandas as pd

_SEMVER_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)(?:[.\-+][a-zA-Z0-9._+-]*)?$"
)
# v1/v4: fix, hotfix ou revert nos commits
_CORRETIVO_V1_RE = re.compile(r"\b(fix|hotfix|revert)\b", re.IGNORECASE)
# v2: apenas hotfix ou revert (sem "fix" simples)
_CORRETIVO_V2_RE = re.compile(r"\b(hotfix|revert)\b", re.IGNORECASE)
# v4: palavras chave de correção nas notas da release
_NOTAS_CORRETIVO_RE = re.compile(
    r"\b(fix|bug|hotfix|revert|regression|patch|security|vulnerability|cve|crash)\b",
    re.IGNORECASE,
)

VarianteHeuristica = Literal["v1", "v2", "v3", "v4", "v5"]


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
    variante: VarianteHeuristica = "v1",
    notas: str = "",
    pct_threshold: float = 0.20,
) -> bool:
    """True se a release é corretiva segundo a variante escolhida.

    v1 (padrão): só o patch mudou OU algum commit tem fix/hotfix/revert.
    v2: só o patch mudou OU algum commit tem hotfix/revert (sem plain "fix").
    v3: só o patch mudou OU >pct_threshold dos commits têm "fix".
    v4: v1 OU as notas da release contêm palavra-chave de correção.
    v5 (refinada): só o patch mudou OU hotfix/revert OU >15% dos commits
        têm "fix" OU as notas contêm palavra-chave de correção.
        Reduz falsos positivos causados por releases com apenas 1 commit
        de "fix: typo" entre muitas features.
    """
    sv_ant = parse_semver(tag_anterior)
    sv_atu = parse_semver(tag_atual)
    so_patch = (
        sv_ant is not None
        and sv_atu is not None
        and sv_ant[0] == sv_atu[0]
        and sv_ant[1] == sv_atu[1]
        and sv_atu[2] > sv_ant[2]
    )

    if variante == "v2":
        tem_commit_fix = (
            not commits_intervalo.empty
            and commits_intervalo["mensagem"].apply(
                lambda m: bool(_CORRETIVO_V2_RE.search(str(m)))
            ).any()
        )
        return bool(so_patch or tem_commit_fix)

    if variante == "v3":
        if commits_intervalo.empty:
            tem_commit_fix = False
        else:
            pct_fix = commits_intervalo["mensagem"].apply(
                lambda m: bool(_CORRETIVO_V1_RE.search(str(m)))
            ).mean()
            tem_commit_fix = float(pct_fix) > pct_threshold
        return bool(so_patch or tem_commit_fix)

    # v1, v4 e v5 compartilham a detecção por commits
    tem_commit_fix = (
        not commits_intervalo.empty
        and commits_intervalo["mensagem"].apply(
            lambda m: bool(_CORRETIVO_V1_RE.search(str(m)))
        ).any()
    )

    if variante == "v4":
        tem_notas_fix = bool(_NOTAS_CORRETIVO_RE.search(str(notas)))
        return bool(so_patch or tem_commit_fix or tem_notas_fix)

    if variante == "v5":
        # hotfix/revert como sinal forte; exige >15% de commits com "fix" para
        # não confundir releases de features com um único "fix: typo" commit.
        if commits_intervalo.empty:
            pct_fix = 0.0
            tem_hotfix = False
        else:
            pct_fix = float(commits_intervalo["mensagem"].apply(
                lambda m: bool(_CORRETIVO_V1_RE.search(str(m)))
            ).mean())
            tem_hotfix = bool(commits_intervalo["mensagem"].apply(
                lambda m: bool(_CORRETIVO_V2_RE.search(str(m)))
            ).any())
        tem_notas_fix = bool(_NOTAS_CORRETIVO_RE.search(str(notas)))
        return bool(so_patch or tem_hotfix or pct_fix > 0.15 or tem_notas_fix)

    # v1 (default)
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
    variante: VarianteHeuristica = "v1",
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
            notas_prox = str(prox.get("body", "")) if variante == "v4" else ""
            if eh_corretiva(rel["tag"], prox["tag"], commits_prox,
                            variante=variante, notas=notas_prox):
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
    variante: VarianteHeuristica = "v1",
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
            notas_prox = str(prox.get("body", "")) if variante == "v4" else ""
            if eh_corretiva(rel["tag"], prox["tag"], commits_prox,
                            variante=variante, notas=notas_prox):
                h = (_para_utc(prox["publicada_em"]) - pub_dt).total_seconds() / 3600
                horas.append(h)
                break

    return pd.Series(horas)


def rework_rate(
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    limite_dias: int | None = None,
    variante: VarianteHeuristica = "v1",
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
        notas_rel = str(rel.get("body", "")) if variante == "v4" else ""
        if eh_corretiva(ant["tag"], rel["tag"], commits_rel,
                        variante=variante, notas=notas_rel):
            corretivas += 1

    if avaliadas == 0:
        return float("nan")
    return corretivas / avaliadas
