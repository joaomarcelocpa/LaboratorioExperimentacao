"""Issues de bug, para o CFR (c): falha medida pelo que os usuários reportam.

Uma issue só vira falha de uma release se ela cita a tag; `cita_tag` guarda
essa informação por issue, e quem decide o que fazer com ela é metricas.cfr.
"""
from __future__ import annotations

import logging
import re
from datetime import date

import pandas as pd

from coleta import http
from metricas.schemas import SCHEMAS, validar

API = "https://api.github.com"

_log = logging.getLogger(__name__)


def _variantes(tag: str) -> list[str]:
    """A tag como escrita no repositório e com o 'v' trocado.

    Quem reporta o bug escreve "1.4.2" para a tag v1.4.2 e vice-versa.
    """
    tag = tag.strip()
    if not tag:
        return []
    if re.match(r"^[vV]\d", tag):
        return [tag, tag[1:]]
    if tag[0].isdigit():
        return [tag, f"v{tag}"]
    return [tag]


def _regex_da_tag(tag: str) -> re.Pattern[str] | None:
    """Casa a tag como palavra inteira.

    Sem as âncoras, a tag v1.2 casaria dentro de v1.2.3 e de v1.20, e a issue
    seria atribuída à release errada. O ponto final de uma frase ("quebrou na
    v1.2.") não impede o casamento; um ponto seguido de dígito, sim.
    """
    variantes = _variantes(tag)
    if not variantes:
        return None
    alternativas = "|".join(re.escape(v) for v in variantes)
    return re.compile(rf"(?<![\w.])(?:{alternativas})(?!\w|\.\d)", re.IGNORECASE)


def cita_alguma_tag(titulo: str | None, corpo: str | None, tags: list[str]) -> bool:
    texto = f"{titulo or ''}\n{corpo or ''}"
    for tag in tags:
        regex = _regex_da_tag(tag)
        if regex is not None and regex.search(texto):
            return True
    return False


def coletar_issues_bug(
    repo: str, labels: list[str], inicio: date, tags: list[str]
) -> list[dict]:
    """Issues (não PRs) com algum dos labels de bug, atualizadas desde `inicio`.

    `since` filtra por atualização, não por criação: uma issue velha mexida na
    janela vem junto. A data de criação vai na linha para quem analisa
    decidir. A mesma issue com dois labels aparece uma vez só.

    Issues desligadas no repositório (410) ou repositório sem acesso (404)
    dão lista vazia: sem issues, o CFR (c) fica nulo para ele.
    """
    por_numero: dict[int, dict] = {}
    desde = f"{inicio.isoformat()}T00:00:00Z"

    for label in labels:
        try:
            itens = http.paginar(
                f"{API}/repos/{repo}/issues",
                {"state": "all", "labels": label, "since": desde},
            )
        except http.ErroDeHTTP as e:
            if e.status in (404, 410):
                _log.warning("%s: issues indisponíveis (%s)", repo, e.status)
                return []
            raise

        for item in itens:
            if "pull_request" in item:
                continue
            numero = int(item["number"])
            if numero in por_numero:
                continue
            nomes = [l["name"] for l in item.get("labels", [])]
            por_numero[numero] = {
                "repo": repo,
                "numero": numero,
                "criada_em": item["created_at"],
                "labels": ";".join(nomes),
                "titulo": item.get("title") or "",
                "cita_tag": cita_alguma_tag(item.get("title"), item.get("body"), tags),
            }

    return [por_numero[n] for n in sorted(por_numero)]


def df_issues_bug(linhas: list[dict]) -> pd.DataFrame:
    """DataFrame no contrato de issues_bug.csv, validado antes de sair."""
    df = pd.DataFrame(linhas, columns=list(SCHEMAS["issues_bug"].colunas))
    if df.empty:
        df["cita_tag"] = df["cita_tag"].astype(bool)
    validar(df, SCHEMAS["issues_bug"])
    return df
