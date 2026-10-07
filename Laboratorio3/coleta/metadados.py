"""Metadados do repositório: os fatores da RQ 06 que vêm direto da API.

Tudo passa por coleta.http, então cache, rate limit e custo valem aqui também.
As funções devolvem dicionários já com as colunas de repos.csv; a montagem do
CSV inteiro, com os fatores de coleta.fatores, está em `coletar_repos`.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone

import pandas as pd

from coleta import http
from coleta.fatores import automacao_release, pct_conventional
from metricas.schemas import SCHEMAS, validar
from pipeline.config import Config

API = "https://api.github.com"

_RE_PAGINA = re.compile(r"[?&]page=(\d+)")

_log = logging.getLogger(__name__)


def contar_contribuidores(repo: str) -> int | None:
    """Contribuidores (anônimos incluídos) pelo truque do per_page=1.

    Com uma contribuição por página, o número da última página é o total. Sem
    cabeçalho Link há uma página só: o total é o tamanho da lista (0 ou 1).

    None quando a API recusa listar, o que acontece em repositórios enormes
    ("The history or contributor list is too large", 403): nulo diz "não deu
    para medir", e zero diria "ninguém contribuiu".
    """
    url = f"{API}/repos/{repo}/contributors"
    try:
        r = http.get(url, {"per_page": 1, "anon": "true"})
    except http.ErroDeHTTP as e:
        if e.status in (403, 451):
            _log.warning("%s: contribuidores indisponíveis (%s)", repo, e.status)
            return None
        raise
    if r.status == 404:
        return None
    ultima = http.links(r.cabecalhos).get("last")
    if ultima is None:
        return len(r.json())
    m = _RE_PAGINA.search(ultima)
    if m is None:
        raise ValueError(f"rel=\"last\" sem número de página: {ultima}")
    return int(m.group(1))


def org_verificada(owner: str, owner_tipo: str) -> bool:
    """`is_verified` da organização; usuário nunca é verificado."""
    if owner_tipo != "Organization":
        return False
    r = http.get(f"{API}/orgs/{owner}")
    if r.status == 404:
        return False
    return bool(r.json().get("is_verified", False))


def idade_em_anos(criado_em: str, fim: date) -> float:
    """Idade do repositório no fim da janela (e não hoje), para que rodar o
    estudo de novo mais tarde não mude o fator."""
    criado = datetime.fromisoformat(criado_em.replace("Z", "+00:00"))
    limite = datetime(fim.year, fim.month, fim.day, 23, 59, 59, tzinfo=timezone.utc)
    return (limite - criado).total_seconds() / (365.25 * 86400)


def coletar_metadados(repo: str, fim: date) -> dict:
    """Colunas de repos.csv que vêm de repos/{owner}/{repo}, orgs e contributors."""
    r = http.get(f"{API}/repos/{repo}")
    if r.status == 404:
        raise http.ErroDeHTTP(f"repositório {repo} não existe mais", 404)
    d = r.json()
    dono = d["owner"]
    return {
        "repo": repo,
        "estrelas": int(d["stargazers_count"]),
        "linguagem": d.get("language"),
        "criado_em": d["created_at"],
        "idade_anos": idade_em_anos(d["created_at"], fim),
        "default_branch": d["default_branch"],
        "contribuidores": contar_contribuidores(repo),
        "owner_tipo": dono["type"],
        "org_verificada": org_verificada(dono["login"], dono["type"]),
    }


def coletar_repos(
    repos: list[str], cfg: Config, commits: pd.DataFrame
) -> pd.DataFrame:
    """repos.csv completo, validado antes de sair.

    `commits` é o commits.csv da coleta: de lá sai o pct_conventional. Um
    repositório que falha na coleta é registrado e fica de fora em vez de
    derrubar os outros; o chamador vê a diferença pelo tamanho do resultado.
    """
    linhas: list[dict] = []
    for repo in repos:
        try:
            linha = coletar_metadados(repo, cfg.janela_fim)
            tem_automacao, ferramenta = automacao_release(repo, linha["default_branch"])
        except http.ErroDeHTTP as e:
            if e.status == 401:
                raise
            _log.warning("%s fora de repos.csv: %s", repo, e)
            continue
        mensagens = commits.loc[commits["repo"] == repo, ["sha", "mensagem"]]
        linha["automacao_release"] = tem_automacao
        linha["ferramenta_release"] = ferramenta
        linha["pct_conventional"] = pct_conventional(mensagens)
        linhas.append(linha)

    df = pd.DataFrame(linhas, columns=list(SCHEMAS["repos"].colunas))
    validar(df, SCHEMAS["repos"])
    return df

