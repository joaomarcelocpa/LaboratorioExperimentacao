"""Coleta commits entre releases via GET /compare/{base}...{head}."""
from __future__ import annotations

import re

import pandas as pd
import requests

from metricas.schemas import SCHEMAS, df_vazio
from pipeline.config import Config

BASE = "https://api.github.com"


def _paginar_compare(
    session: requests.Session,
    url: str,
) -> tuple[list[dict], bool]:
    """Retorna (commits, houve_404)."""
    commits: list[dict] = []
    page = 1
    base_url = url
    while True:
        paginado = base_url if page == 1 else f"{base_url}?page={page}"
        r = session.get(paginado)
        if r.status_code == 404:
            return [], True
        r.raise_for_status()
        data = r.json()
        novos = data.get("commits", [])
        commits.extend(novos)
        link = r.headers.get("Link", "")
        if not re.search(r'rel="next"', link):
            break
        page += 1
    return commits, False


def coletar_commits(
    repo: str,
    releases_df: pd.DataFrame,
    cfg: Config,
    session: requests.Session,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (commits_df, releases_ignoradas_df)."""
    na_janela = releases_df[releases_df["na_janela"]].sort_values("publicada_em")
    todas = releases_df.sort_values("publicada_em")

    commit_linhas: list[dict] = []
    ignoradas_linhas: list[dict] = []

    for _, rel in na_janela.iterrows():
        tag_head = rel["tag"]
        anteriores = todas[todas["publicada_em"] < rel["publicada_em"]]
        if anteriores.empty:
            ignoradas_linhas.append({
                "repo": repo,
                "tag": tag_head,
                "motivo": "sem release anterior",
            })
            continue

        tag_base = anteriores.sort_values("publicada_em").iloc[-1]["tag"]
        url = f"{BASE}/repos/{repo}/compare/{tag_base}...{tag_head}"
        raw_commits, houve_404 = _paginar_compare(session, url)

        if houve_404:
            ignoradas_linhas.append({
                "repo": repo,
                "tag": tag_head,
                "motivo": f"404 em compare/{tag_base}...{tag_head}",
            })
            continue

        for c in raw_commits:
            login = (c.get("author") or {}).get("login", "")
            eh_bot = login.endswith("[bot]") or login in cfg.bots
            commit_linhas.append({
                "repo": repo,
                "release_tag": tag_head,
                "sha": c["sha"],
                "data_autor": c["commit"]["author"]["date"],
                "autor_login": login,
                "eh_bot": eh_bot,
                "mensagem": c["commit"]["message"],
            })

    commits_df = pd.DataFrame(commit_linhas) if commit_linhas else df_vazio(SCHEMAS["commits"])
    ignoradas_df = (pd.DataFrame(ignoradas_linhas) if ignoradas_linhas
                    else df_vazio(SCHEMAS["releases_ignoradas"]))
    return commits_df, ignoradas_df
