"""Tempo de recuperação após falha de CI (RQ 04).

Um episódio começa na primeira falha APÓS um sucesso e termina no próximo
sucesso do mesmo workflow. Episódios que não terminam até o fim dos dados são
censurados: entram no CSV marcados, mas ficam fora da mediana, porque não têm
duração conhecida.

recuperacao_h sai dos episódios de runs.csv, como a RQ 04 define;
recuperacao_sem_flaky usa a linha do tempo bruta. São populações diferentes,
e o artigo precisa dizer isso ao compará-las.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from metricas.execucoes import linha_do_tempo, marcar_flaky
from metricas.schemas import SCHEMAS

COLUNAS_EPISODIO = list(SCHEMAS["episodios"].colunas)


@dataclass(frozen=True)
class Episodios:
    df: pd.DataFrame
    # Falhas que não abriram episódio por não haver sucesso antes delas.
    # Censura à esquerda: não se sabe quando a quebra começou. Contadas em vez
    # de descartadas em silêncio, que faria o repo parecer mais estável.
    falhas_sem_sucesso_anterior: int


def episodios(
    runs: pd.DataFrame, attempts: pd.DataFrame | None = None
) -> Episodios:
    """Episódios sobre runs.csv, com so_flaky visto da linha do tempo inteira.

    Os episódios são construídos só sobre as execuções que vieram de runs —
    é o conjunto que a RQ 04 define e que alimenta a classificação DORA. Mas
    a marcação de flaky usa runs e tentativas, porque é a visão completa que
    diz se uma falha foi instabilidade.
    """
    completa = marcar_flaky(linha_do_tempo(runs, attempts))
    so_runs = completa[completa["origem"] == "run"]
    return _construir(so_runs)


def recuperacao_sem_flaky(
    runs: pd.DataFrame, attempts: pd.DataFrame | None = None
) -> float:
    """Mediana da recuperação sobre a linha do tempo bruta, sem os só-flaky."""
    completa = marcar_flaky(linha_do_tempo(runs, attempts))
    df = _construir(completa).df
    if df.empty:
        return math.nan
    return mediana_horas(df[~df["so_flaky"].astype(bool)])


def _construir(execucoes: pd.DataFrame) -> Episodios:
    linhas: list[dict] = []
    sem_sucesso_anterior = 0

    if execucoes.empty:
        return Episodios(pd.DataFrame(columns=COLUNAS_EPISODIO), 0)

    for (repo, workflow_id), grupo in execucoes.groupby(
        ["repo", "workflow_id"], dropna=False, sort=False
    ):
        # Só sucesso e falha movem a máquina: ignorado nem abre nem fecha.
        relevantes = grupo[grupo["classe"].isin(["sucesso", "falha"])]
        viu_sucesso = False
        aberto: dict | None = None

        for _, execucao in relevantes.iterrows():
            if execucao["classe"] == "falha":
                if not viu_sucesso:
                    sem_sucesso_anterior += 1
                elif aberto is None:
                    aberto = {"inicio": execucao["inicio"],
                              "flaky": [bool(execucao["flaky"])]}
                else:
                    aberto["flaky"].append(bool(execucao["flaky"]))
                continue

            # sucesso
            viu_sucesso = True
            if aberto is not None:
                linhas.append(_fechado(repo, workflow_id, aberto, execucao["fim"]))
                aberto = None

        if aberto is not None:
            linhas.append(_censurado(repo, workflow_id, aberto))

    df = pd.DataFrame(linhas, columns=COLUNAS_EPISODIO)
    return Episodios(df, sem_sucesso_anterior)


def _fechado(repo, workflow_id, aberto: dict, fim) -> dict:
    # Sem as duas pontas não dá para saber quanto durou. Fechar com horas=NaN
    # e censurado=False faria o episódio sumir das duas contas e contradiria
    # o CSV, onde `fim` vazio é justamente a marca da censura.
    if pd.isna(fim) or pd.isna(aberto["inicio"]):
        return _censurado(repo, workflow_id, aberto)
    horas = (fim - aberto["inicio"]).total_seconds() / 3600
    return {
        "repo": repo, "workflow_id": workflow_id,
        "inicio": aberto["inicio"], "fim": fim, "horas": horas,
        "censurado": False, "so_flaky": all(aberto["flaky"]),
    }


def _censurado(repo, workflow_id, aberto: dict) -> dict:
    return {
        "repo": repo, "workflow_id": workflow_id,
        "inicio": aberto["inicio"], "fim": pd.NaT, "horas": math.nan,
        "censurado": True, "so_flaky": all(aberto["flaky"]),
    }


def mediana_horas(episodios: pd.DataFrame) -> float:
    """Mediana das horas, ignorando os censurados.

    NaN quando não sobra episódio: zero diria "recuperação instantânea".
    """
    if episodios.empty:
        return math.nan
    fechados = episodios[~episodios["censurado"].astype(bool)]
    if fechados.empty:
        return math.nan
    return float(fechados["horas"].median())


def pct_censurados(episodios: pd.DataFrame) -> float:
    """Censurados ÷ total. NaN quando não houve episódio nenhum."""
    if episodios.empty:
        return math.nan
    return float(episodios["censurado"].astype(bool).sum()) / len(episodios)
