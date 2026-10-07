"""Change failure rate medido pelo CI (RQ 03a), nas três versões.

A hierarquia importa: o oficial vê só runs.csv, onde uma falha recuperada por
re-run é invisível; o bruto acrescenta as tentativas anteriores; e o sem-flaky
parte do BRUTO, nunca do oficial — tirar flaky do oficial não faria sentido,
porque as flaky que o re-run resolveu nem estão lá.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from metricas.execucoes import linha_do_tempo, marcar_flaky


def cfr_ci(
    runs: pd.DataFrame,
    attempts: pd.DataFrame | None = None,
    sem_flaky: bool = False,
) -> float:
    """Falhas ÷ (falhas + sucessos), pela tabela da seção 3.

    `attempts` escolhe o conjunto: sem ele é o oficial, com ele é o bruto.
    `sem_flaky=True` remove as falhas flaky do conjunto escolhido.

    NaN quando não há sucesso nem falha: zero diria "nenhuma mudança falhou",
    que é diferente de "não há dados".
    """
    execucoes = linha_do_tempo(runs, attempts)
    if sem_flaky:
        execucoes = marcar_flaky(execucoes)
        execucoes = execucoes[~execucoes["flaky"]]

    falhas = int((execucoes["classe"] == "falha").sum())
    sucessos = int((execucoes["classe"] == "sucesso").sum())
    total = falhas + sucessos
    return math.nan if total == 0 else falhas / total


def pct_falhas_flaky(
    runs: pd.DataFrame, attempts: pd.DataFrame | None = None
) -> float:
    """Proporção das falhas do CFR bruto que eram instabilidade.

    NaN quando não houve falha nenhuma: zero diria "nenhuma falha era flaky".
    """
    execucoes = marcar_flaky(linha_do_tempo(runs, attempts))
    falhas = execucoes[execucoes["classe"] == "falha"]
    if falhas.empty:
        return math.nan
    return float(falhas["flaky"].sum()) / len(falhas)


MODOS_CFR_ISSUES = ("janela", "citacao")


def _utc(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, utc=True)


def cfr_issues(
    releases: pd.DataFrame,
    issues: pd.DataFrame,
    n_dias: int,
    modo: str,
    janela_fim: date,
) -> float:
    """CFR (c): releases seguidas de uma issue de bug em até `n_dias`.

    Uma release falhou se alguma issue foi criada entre a publicação (dia 0,
    inclusive) e `n_dias` dias depois (inclusive). Uma issue criada antes da
    release não conta, e uma criada em n_dias + 1 também não.

    `modo="janela"` aceita qualquer issue de bug nesse intervalo.
    `modo="citacao"` exige também `cita_tag`: a issue precisa citar a tag de
    alguma release no título ou no corpo. issues_bug.csv guarda só se alguma
    tag foi citada, não qual; por isso a atribuição à release é pela janela
    de tempo nos dois modos.

    Censura: uma release publicada de modo que `publicada_em + n_dias`
    passe do fim da janela não entra nem no numerador nem no denominador,
    porque ainda não deu tempo de ela falhar. Contá-la como sucesso
    subestimaria o CFR.

    NaN, e não zero, quando o repositório não tem nenhuma issue de bug (sem
    labels de bug não dá para distinguir "nunca falhou" de "não registra
    falhas") ou quando nenhuma release é observável por inteiro.
    """
    if modo not in MODOS_CFR_ISSUES:
        raise ValueError(
            f"modo inválido: {modo!r}. Use um de {', '.join(MODOS_CFR_ISSUES)}."
        )
    if issues.empty:
        return math.nan

    observaveis = releases[releases["na_janela"].astype(bool)] if not releases.empty else releases
    if observaveis.empty:
        return math.nan

    prazo = timedelta(days=n_dias)
    fim_da_janela = datetime.combine(janela_fim, time(23, 59, 59), tzinfo=timezone.utc)
    publicadas = _utc(observaveis["publicada_em"])
    publicadas = publicadas[publicadas + prazo <= fim_da_janela]
    if publicadas.empty:
        return math.nan

    candidatas = issues[issues["cita_tag"].astype(bool)] if modo == "citacao" else issues
    criadas = _utc(candidatas["criada_em"])

    falhas = sum(
        bool(((criadas >= pub) & (criadas - pub <= prazo)).any())
        for pub in publicadas
    )
    return falhas / len(publicadas)
