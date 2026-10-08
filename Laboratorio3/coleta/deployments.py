"""Coleta deployments de ambientes de produção."""
from __future__ import annotations

import re

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
        data = r.json()
        if isinstance(data, list):
            resultados.extend(data)
        else:
            resultados.extend(data.get("deployments", []))
        link = r.headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else ""
    return resultados


def _deployments_rest(
    repo: str, cfg: Config, session: requests.Session
) -> list[dict]:
    """Caminho REST: uma chamada de statuses para cada deployment."""
    r = session.get(f"{BASE}/repos/{repo}/environments")
    r.raise_for_status()
    envs_data = r.json().get("environments", [])
    nomes_envs = {e["name"] for e in envs_data}

    producao = nomes_envs & set(cfg.ambientes_producao)
    linhas: list[dict] = []
    for env in producao:
        url = f"{BASE}/repos/{repo}/deployments?environment={env}&per_page=100"
        for dep in _paginar(session, url):
            dep_id = dep["id"]
            sr = session.get(f"{BASE}/repos/{repo}/deployments/{dep_id}/statuses")
            sr.raise_for_status()
            statuses = sr.json()
            estado_final = statuses[0]["state"] if statuses else "desconhecido"
            linhas.append({
                "repo": repo,
                "id": dep_id,
                "environment": dep["environment"],
                "criado_em": dep["created_at"],
                "sha": dep["sha"],
                "estado_final": estado_final,
            })
    return linhas


def coletar_deployments(
    repo: str,
    cfg: Config,
    session: requests.Session,
) -> pd.DataFrame:
    """Retorna deployments_df com estado_final de cada deployment de produção.

    A sessão do pipeline sabe pedir isso ao GraphQL, 100 deployments por
    chamada; sem ela (ou se o repositório não for achado pelo nome), a REST
    faz uma chamada de statuses por deployment.
    """
    linhas: list[dict] | None = None
    if hasattr(session, "deployments_com_estado"):
        linhas = session.deployments_com_estado(repo, list(cfg.ambientes_producao))
    if linhas is None:
        linhas = _deployments_rest(repo, cfg, session)
    return pd.DataFrame(linhas) if linhas else df_vazio(SCHEMAS["deployments"])
