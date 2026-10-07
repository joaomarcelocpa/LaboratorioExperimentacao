"""Critérios de inclusão aplicados aos candidatos, e o sorteio da amostra.

Os filtros rodam do mais barato ao mais caro, para que um repositório
descartado cedo não gaste chamadas das etapas seguintes:

    1. usa GitHub Actions        (1 chamada)
    2. >= min_releases na janela (1 a poucas páginas)
    3. >= min_runs válidos       (até 4 chamadas + 1 do default branch)
    4. sorteio de n_repos com seed

Cada descarte vai para descartes.csv com o motivo, e cada etapa vira uma
linha de funil.csv. O funil fecha: o que entra numa etapa menos o que sai
dela é o que entra na seguinte.
"""
from __future__ import annotations

import logging
import random
from datetime import date, datetime, timezone

import pandas as pd

from coleta import http
from metricas.schemas import SCHEMAS, validar
from pipeline.config import Config

API = "https://api.github.com"

# Valores de `status=` que a API aceita para filtrar por conclusion, os
# mesmos que coleta.runs classifica como sucesso ou falha.
CONCLUSIONS_VALIDAS = ("success", "failure", "timed_out", "startup_failure")

_log = logging.getLogger(__name__)


def _momento(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def usa_actions(repo: str) -> bool:
    """O repositório tem ao menos um workflow?"""
    r = http.get(f"{API}/repos/{repo}/actions/workflows", {"per_page": 1})
    if r.status == 404:
        return False
    return int(r.json().get("total_count", 0)) > 0


def releases_na_janela(repo: str, inicio: date, fim: date) -> int:
    """Releases publicadas na janela, sem rascunhos.

    Pré-releases contam: o estudo as trata como releases (freq_release_pre
    existe justamente para compará-las).
    """
    try:
        itens = http.paginar(f"{API}/repos/{repo}/releases")
    except http.ErroDeHTTP as e:
        if e.status == 404:
            return 0
        raise
    de = datetime(inicio.year, inicio.month, inicio.day, tzinfo=timezone.utc)
    ate = datetime(fim.year, fim.month, fim.day, 23, 59, 59, tzinfo=timezone.utc)
    total = 0
    for rel in itens:
        if rel.get("draft"):
            continue
        publicada = _momento(rel.get("published_at"))
        if publicada is not None and de <= publicada <= ate:
            total += 1
    return total


def runs_validos(
    repo: str, inicio: date, fim: date, minimo: int
) -> int:
    """Runs de push do default branch na janela, com sucesso ou falha.

    Conta pelo total_count de consultas com per_page=1, sem baixar os runs: o
    filtro só precisa saber se passa de `minimo`, e para assim que passa.
    A coleta de verdade (coleta.runs) vem depois, só para quem entrou.
    """
    r = http.get(f"{API}/repos/{repo}")
    if r.status == 404:
        return 0
    branch = r.json().get("default_branch")
    if not branch:
        return 0

    total = 0
    for conclusion in CONCLUSIONS_VALIDAS:
        resposta = http.get(
            f"{API}/repos/{repo}/actions/runs",
            {
                "branch": branch,
                "event": "push",
                "status": conclusion,
                "created": f"{inicio.isoformat()}..{fim.isoformat()}",
                "per_page": 1,
            },
        )
        total += int(resposta.json().get("total_count", 0))
        if total >= minimo:
            break
    return total


def _passa(repo: str, etapa: str, cfg: Config) -> bool:
    if etapa == "usa_actions":
        return usa_actions(repo)
    if etapa == "min_releases":
        n = releases_na_janela(repo, cfg.janela_inicio, cfg.janela_fim)
        return n >= cfg.min_releases
    if etapa == "min_runs":
        n = runs_validos(repo, cfg.janela_inicio, cfg.janela_fim, cfg.min_runs)
        return n >= cfg.min_runs
    raise ValueError(f"etapa desconhecida: {etapa}")


ETAPAS = ("usa_actions", "min_releases", "min_runs")


def filtrar(
    repos: list[str], cfg: Config
) -> tuple[list[str], list[dict], list[dict]]:
    """Aplica as três etapas em ordem. Devolve (aprovados, descartes, funil).

    Um erro de API num repositório (403, 451...) o descarta com o status no
    motivo em vez de derrubar a seleção inteira: perder um repositório custa
    menos do que perder horas de coleta. Um 401 continua estourando, porque
    esconder um token errado atrás de um funil vazio é pior.
    """
    restantes = list(repos)
    descartes: list[dict] = []
    funil: list[dict] = []

    for etapa in ETAPAS:
        entraram = len(restantes)
        mantidos: list[str] = []
        for repo in restantes:
            try:
                ok = _passa(repo, etapa, cfg)
                motivo = _motivo_da_etapa(etapa, cfg)
            except http.ErroDeHTTP as e:
                if e.status == 401:
                    raise
                ok, motivo = False, f"erro de API ({e.status}) em {etapa}"
                _log.warning("%s descartado em %s: %s", repo, etapa, e)
            if ok:
                mantidos.append(repo)
            else:
                descartes.append({"repo": repo, "etapa": etapa, "motivo": motivo})
        restantes = mantidos
        funil.append({
            "etapa": etapa,
            "entraram": entraram,
            "sairam": entraram - len(restantes),
            "motivo": _motivo_da_etapa(etapa, cfg),
        })

    return restantes, descartes, funil


def _motivo_da_etapa(etapa: str, cfg: Config) -> str:
    return {
        "usa_actions": "não usa GitHub Actions",
        "min_releases": f"menos de {cfg.min_releases} releases na janela",
        "min_runs": f"menos de {cfg.min_runs} runs válidos na janela",
    }[etapa]


def sortear(
    aprovados: list[str], n_repos: int, seed: int
) -> tuple[list[str], list[dict], dict]:
    """Amostra de `n_repos` com semente fixa. Devolve (amostra, descartes, funil).

    A entrada é ordenada antes do sorteio: a mesma semente só reproduz a
    mesma amostra se não depender da ordem em que os repositórios chegaram.
    Com menos aprovados que `n_repos`, todos entram e o funil não perde nada.
    """
    ordenados = sorted(aprovados)
    if len(ordenados) <= n_repos:
        escolhidos = ordenados
    else:
        escolhidos = sorted(random.Random(seed).sample(ordenados, n_repos))

    fora = sorted(set(ordenados) - set(escolhidos))
    motivo = f"fora da amostra sorteada (n_repos={n_repos}, seed={seed})"
    descartes = [{"repo": r, "etapa": "sorteio", "motivo": motivo} for r in fora]
    funil = {
        "etapa": "sorteio",
        "entraram": len(ordenados),
        "sairam": len(fora),
        "motivo": motivo,
    }
    return escolhidos, descartes, funil


def funil_fecha(funil: pd.DataFrame, final: int) -> bool:
    """A soma fecha? Entrada menos saídas de cada etapa é a entrada da próxima,
    e a última sobra é a amostra final."""
    esperado = None
    for _, linha in funil.iterrows():
        if esperado is not None and int(linha["entraram"]) != esperado:
            return False
        esperado = int(linha["entraram"]) - int(linha["sairam"])
    return esperado == final


def df_funil(linhas: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(linhas, columns=list(SCHEMAS["funil"].colunas))
    validar(df, SCHEMAS["funil"])
    return df


def df_descartes(linhas: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(linhas, columns=list(SCHEMAS["descartes"].colunas))
    validar(df, SCHEMAS["descartes"])
    return df
