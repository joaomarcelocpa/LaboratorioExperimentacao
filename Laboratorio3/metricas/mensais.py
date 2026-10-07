"""Séries mensais de CFR e recuperação (RQ 08b).

Uma função só monta o frame inteiro porque metricas_mensais.csv tem cfr_a,
recuperacao_h e runs_validos na MESMA linha, e a regra _mes_pobre_e_nulo do
contrato cruza as três: ela só pode ser aplicada depois da junção.
"""
from __future__ import annotations

import math

import pandas as pd

from metricas.cfr import cfr_ci
from metricas.execucoes import momento
from metricas.recuperacao import episodios, mediana_horas
from metricas.schemas import SCHEMAS, validar

COLUNAS_MENSAIS = list(SCHEMAS["metricas_mensais"].colunas)


def series_mensais(
    runs: pd.DataFrame,
    attempts: pd.DataFrame | None = None,
    min_runs_mes: int = 5,
) -> pd.DataFrame:
    """Uma linha por (repo, mês), validada contra o contrato antes de sair.

    O mês de um run sai de criado_em, para bater com o critério da janela do
    enunciado. O mês de um episódio é o da sua primeira falha, e os episódios
    são calculados sobre a janela inteira antes de serem distribuídos — um
    episódio que atravessa a virada do mês conta no mês em que começou.
    """
    if runs.empty:
        return pd.DataFrame(columns=COLUNAS_MENSAIS)

    base = runs.copy()
    base["_mes"] = momento(base["criado_em"]).dt.strftime("%Y-%m")

    eps = episodios(runs, attempts).df
    if not eps.empty:
        eps = eps.assign(_mes=momento(eps["inicio"]).dt.strftime("%Y-%m"))

    linhas = []
    for (repo, mes), do_mes in base.groupby(["repo", "_mes"], dropna=False,
                                            sort=True):
        validos = int(do_mes["classe"].isin(["sucesso", "falha"]).sum())
        pobre = validos < min_runs_mes
        linhas.append({
            "repo": repo,
            "mes": mes,
            "cfr_a": math.nan if pobre else cfr_ci(do_mes),
            "recuperacao_h": math.nan if pobre else _recuperacao_do_mes(eps, repo, mes),
            "runs_validos": validos,
        })

    df = pd.DataFrame(linhas, columns=COLUNAS_MENSAIS)
    validar(df, SCHEMAS["metricas_mensais"])
    return df


def _recuperacao_do_mes(eps: pd.DataFrame, repo: str, mes: str) -> float:
    if eps.empty:
        return math.nan
    do_mes = eps[(eps["repo"] == repo) & (eps["_mes"] == mes)]
    return mediana_horas(do_mes)
