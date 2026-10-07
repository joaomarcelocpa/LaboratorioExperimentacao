"""Linha do tempo única de execuções de CI, com marcação de flaky.

A listagem de /actions/runs mostra só a última tentativa de cada run: uma
falha recuperada por re-run simplesmente não aparece ali. Juntar runs e
tentativas anteriores numa tabela só é o que torna visível a diferença entre
o CFR oficial e o bruto.

Esta primitiva é compartilhada: o CFR usa a marcação de flaky para o
cfr_a_sem_flaky, e os episódios a usam para o so_flaky.
"""
from __future__ import annotations

import pandas as pd

# run_attempts.csv traz conclusion, não classe: a tabela da seção 3 mora na
# coleta e não pode ser duplicada aqui. O import não forma ciclo, porque
# coleta.runs importa metricas.schemas, que não importa este módulo.
from coleta.runs import classificar

COLUNAS_EXECUCAO = [
    "repo", "workflow_id", "head_sha", "classe", "origem",
    "inicio", "fim", "criado_em", "ordem",
]


def momento(valor):
    """Texto ISO ou datetime vira Timestamp UTC; o que não dá vira NaT.

    pd.read_csv devolve texto, mas um chamador pode já ter convertido — as
    duas formas precisam dar o mesmo resultado.
    """
    return pd.to_datetime(valor, utc=True, errors="coerce")


def linha_do_tempo(
    runs: pd.DataFrame, attempts: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Runs e tentativas anteriores numa só tabela, ordenada no tempo."""
    partes = [_de_runs(runs)]
    if attempts is not None and not attempts.empty:
        partes.append(_de_tentativas(runs, attempts))

    # Partes vazias fora do concat: incluí-las faz o pandas inferir dtype a
    # partir de colunas todas-NA, o que ele já avisa que vai deixar de fazer.
    cheias = [p for p in partes if not p.empty]
    if not cheias:
        return pd.DataFrame(columns=COLUNAS_EXECUCAO)
    juntas = pd.concat(cheias, ignore_index=True)
    # NaT por último: um run sem data não ancora episódio nem quebra ordem.
    juntas = juntas.sort_values(
        ["inicio", "ordem"], na_position="last", kind="stable"
    ).reset_index(drop=True)
    return juntas[COLUNAS_EXECUCAO]


def _de_runs(runs: pd.DataFrame) -> pd.DataFrame:
    if runs.empty:
        return pd.DataFrame(columns=COLUNAS_EXECUCAO)
    return pd.DataFrame({
        "repo": runs["repo"],
        "workflow_id": runs["workflow_id"],
        "head_sha": runs["head_sha"],
        "classe": runs["classe"],
        "origem": "run",
        "inicio": momento(runs["inicio"]),
        "fim": momento(runs["fim"]),
        "criado_em": momento(runs["criado_em"]),
        "ordem": runs["run_attempt"],
    })


def _de_tentativas(runs: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    """Tentativas anteriores, herdando o contexto do seu run.

    run_attempts.csv não tem workflow_id, head_sha nem criado_em: os três vêm
    da junção por run_id. Uma tentativa órfã — run_id que não existe em runs —
    é descartada, porque entraria com workflow_id nulo e corromperia os grupos
    de flaky e os episódios.
    """
    contexto = runs[["run_id", "workflow_id", "head_sha", "criado_em"]]
    juntas = attempts.merge(contexto, on="run_id", how="inner")
    if juntas.empty:
        return pd.DataFrame(columns=COLUNAS_EXECUCAO)
    # NaN é truthy, então o `(conclusion or "")` de classificar o deixaria
    # passar e o .strip() seguinte estouraria. Célula vazia de CSV vira NaN.
    # A conversão é feita item a item de propósito: num dtype float64,
    # Series.where(..., None) recoloca NaN, porque None não cabe ali.
    conclusoes = [None if pd.isna(c) else c for c in juntas["conclusion"]]
    return pd.DataFrame({
        "repo": juntas["repo"],
        "workflow_id": juntas["workflow_id"],
        "head_sha": juntas["head_sha"],
        "classe": [classificar(c) for c in conclusoes],
        "origem": "tentativa",
        "inicio": momento(juntas["inicio"]),
        "fim": momento(juntas["fim"]),
        "criado_em": momento(juntas["criado_em"]),
        "ordem": juntas["tentativa"],
    })


def marcar_flaky(execucoes: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta `flaky`: a falha teve um sucesso posterior no mesmo sha.

    "Posterior" é qualquer sucesso depois dela no mesmo workflow_id e
    head_sha, não só o adjacente: se o mesmo código acabou passando sem
    alteração nenhuma, nenhuma daquelas falhas era defeito. Execuções de
    classe `ignorado` não entram na conta nem interrompem a cadeia, porque a
    comparação é por posição na ordem, e elas só ocupam posição.
    """
    df = execucoes.copy()
    if df.empty:
        df["flaky"] = pd.Series(dtype=bool)
        return df

    ordem = pd.Series(range(len(df)), index=df.index)
    posicao_dos_sucessos = ordem.where(df["classe"] == "sucesso")
    # dropna=False: head_sha nulo é uma chave legítima. Sem isto, as falhas
    # desses runs nunca seriam marcadas e ninguém perceberia.
    ultimo_sucesso = posicao_dos_sucessos.groupby(
        [df["workflow_id"], df["head_sha"]], dropna=False
    ).transform("max")

    df["flaky"] = (df["classe"] == "falha") & (ordem < ultimo_sucesso)
    return df
