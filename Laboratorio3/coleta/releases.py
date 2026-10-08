"""Coleta releases, pré-releases e tags de um repositório."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from metricas.schemas import SCHEMAS, df_vazio
from pipeline.config import Config

BASE = "https://api.github.com"


def _paginar(session: requests.Session, url: str) -> list[dict]:
    resultados: list[dict] = []
    while url:
        r = session.get(url)
        r.raise_for_status()
        resultados.extend(r.json())
        link = r.headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else ""
    return resultados


def _parse_data(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _tags_rest(session: requests.Session, repo: str) -> list[dict]:
    """Caminho REST: uma chamada a /commits/{sha} para cada tag."""
    linhas: list[dict] = []
    for t in _paginar(session, f"{BASE}/repos/{repo}/tags"):
        sha = t["commit"]["sha"]
        r = session.get(f"{BASE}/repos/{repo}/commits/{sha}")
        r.raise_for_status()
        linhas.append({
            "repo": repo,
            "tag": t["name"],
            "sha": sha,
            "data_commit": r.json()["commit"]["author"]["date"],
        })
    return linhas


def coletar_releases(
    repo: str,
    cfg: Config,
    session: requests.Session,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (releases_df, tags_df).

    releases_df inclui todas as releases sem draft, com flag na_janela.
    Inclui a release imediatamente anterior à janela (base para compare).
    tags_df inclui todas as tags com data_commit (GraphQL, ou REST de reserva).
    """
    inicio = datetime(cfg.janela_inicio.year, cfg.janela_inicio.month,
                      cfg.janela_inicio.day, tzinfo=timezone.utc)
    fim = datetime(cfg.janela_fim.year, cfg.janela_fim.month,
                   cfg.janela_fim.day, 23, 59, 59, tzinfo=timezone.utc)

    raw = _paginar(session, f"{BASE}/repos/{repo}/releases")

    linhas: list[dict] = []
    ultima_antes: dict[str, Any] | None = None

    for rel in raw:
        if rel.get("draft"):
            continue
        pub = _parse_data(rel["published_at"])
        na_janela = inicio <= pub <= fim
        if na_janela:
            linhas.append({
                "repo": repo,
                "tag": rel["tag_name"],
                "publicada_em": rel["published_at"],
                "prerelease": bool(rel.get("prerelease", False)),
                "na_janela": True,
                "body": rel.get("body") or "",
            })
        elif pub < inicio:
            if (ultima_antes is None
                    or _parse_data(rel["published_at"]) > _parse_data(ultima_antes["published_at"])):
                ultima_antes = rel

    if ultima_antes is not None:
        linhas.append({
            "repo": repo,
            "tag": ultima_antes["tag_name"],
            "publicada_em": ultima_antes["published_at"],
            "prerelease": bool(ultima_antes.get("prerelease", False)),
            "na_janela": False,
            "body": ultima_antes.get("body") or "",
        })

    releases_df = pd.DataFrame(linhas) if linhas else df_vazio(SCHEMAS["releases"])

    # tags: com a data do commit. A sessão do pipeline sabe pedir isso ao
    # GraphQL, 100 tags por chamada; sem ela (ou se o repositório não for
    # achado pelo nome), a REST faz uma chamada por tag.
    tag_linhas: list[dict] | None = None
    if hasattr(session, "tags_com_data"):
        tag_linhas = session.tags_com_data(repo)
    if tag_linhas is None:
        tag_linhas = _tags_rest(session, repo)
    tags_df = pd.DataFrame(tag_linhas) if tag_linhas else df_vazio(SCHEMAS["tags"])

    return releases_df, tags_df
