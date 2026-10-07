"""Change failure rate medido pelo CI (RQ 03a), nas três versões.

A hierarquia importa: o oficial vê só runs.csv, onde uma falha recuperada por
re-run é invisível; o bruto acrescenta as tentativas anteriores; e o sem-flaky
parte do BRUTO, nunca do oficial — tirar flaky do oficial não faria sentido,
porque as flaky que o re-run resolveu nem estão lá.
"""
from __future__ import annotations

import math

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
