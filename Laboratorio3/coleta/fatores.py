"""Fatores da RQ 06 que exigem olhar dentro do repositório.

Automação de release (por arquivos de configuração e por menção nos workflows)
e a proporção de commits no padrão Conventional Commits.
"""
from __future__ import annotations

import base64
import fnmatch
import logging
import math
import re

import pandas as pd

from coleta import http

API = "https://api.github.com"

# Ordem = prioridade quando um repositório usa mais de uma ferramenta.
FERRAMENTAS = ("semantic-release", "release-please", "changesets", "goreleaser")

# Arquivo (ou pasta) de configuração na raiz -> ferramenta.
_PADROES_DE_ARQUIVO = (
    (".releaserc*", "semantic-release"),
    ("release-please-config.json", "release-please"),
    (".changeset", "changesets"),
    (".goreleaser.y*ml", "goreleaser"),
)

# Menção num YAML de workflow -> ferramenta. Casa o nome da ferramenta, e não
# um uso qualquer da palavra "release": um workflow que só chama
# `gh release create` não é automação de versionamento.
_PADROES_DE_TEXTO = (
    (re.compile(r"semantic[-_]release", re.IGNORECASE), "semantic-release"),
    (re.compile(r"release[-_]please", re.IGNORECASE), "release-please"),
    (re.compile(r"changesets/action|changeset\s+(?:version|publish)", re.IGNORECASE),
     "changesets"),
    (re.compile(r"goreleaser", re.IGNORECASE), "goreleaser"),
)

# type(escopo)!: descrição — o cabeçalho do Conventional Commits 1.0. Só a
# primeira linha da mensagem conta. Os tipos são os do preset angular, que o
# commitlint e o semantic-release usam por padrão.
_RE_CONVENTIONAL = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([^()\r\n]+\))?!?: \S",
    re.IGNORECASE,
)

_log = logging.getLogger(__name__)


def _prioridade(achadas: set[str]) -> str:
    for ferramenta in FERRAMENTAS:
        if ferramenta in achadas:
            return ferramenta
    return "nenhuma"


def ferramenta_por_arquivos(nomes: list[str]) -> set[str]:
    """Ferramentas indicadas pelos nomes na raiz do repositório."""
    achadas: set[str] = set()
    for nome in nomes:
        for padrao, ferramenta in _PADROES_DE_ARQUIVO:
            if fnmatch.fnmatchcase(nome, padrao):
                achadas.add(ferramenta)
    return achadas


def ferramenta_por_texto(textos: list[str]) -> set[str]:
    """Ferramentas mencionadas nos YAML de workflow."""
    achadas: set[str] = set()
    for texto in textos:
        for regex, ferramenta in _PADROES_DE_TEXTO:
            if regex.search(texto):
                achadas.add(ferramenta)
    return achadas


def _ler_arquivo(repo: str, caminho: str, ref: str) -> str:
    r = http.get(f"{API}/repos/{repo}/contents/{caminho}", {"ref": ref})
    if r.status == 404:
        return ""
    carga = r.json()
    if carga.get("encoding") != "base64":
        return ""
    return base64.b64decode(carga.get("content", "")).decode("utf-8", errors="replace")


def automacao_release(repo: str, default_branch: str) -> tuple[bool, str]:
    """(tem automação, ferramenta) pelos arquivos da raiz e pelos workflows.

    Arquivos pesam mais que menção: quando as duas fontes divergem, vale a
    ferramenta de configuração, que é a que dirige o release.
    `default_branch` fixa a árvore lida, para que o resultado não mude se
    outra branch tiver arquivos diferentes.
    """
    ref = {"ref": default_branch}
    raiz = _listar_com_ref(f"{API}/repos/{repo}/contents/", ref)
    por_arquivo = ferramenta_por_arquivos([i["name"] for i in raiz])

    workflows = [
        i for i in _listar_com_ref(f"{API}/repos/{repo}/contents/.github/workflows", ref)
        if i.get("type") == "file" and i["name"].lower().endswith((".yml", ".yaml"))
    ]
    textos = [_ler_arquivo(repo, i["path"], default_branch) for i in workflows]
    por_texto = ferramenta_por_texto(textos)

    ferramenta = _prioridade(por_arquivo) if por_arquivo else _prioridade(por_texto)
    return ferramenta != "nenhuma", ferramenta


def _listar_com_ref(url: str, params: dict) -> list[dict]:
    r = http.get(url, params)
    if r.status == 404:
        return []
    carga = r.json()
    return carga if isinstance(carga, list) else []


def e_conventional(mensagem: str | None) -> bool:
    """A primeira linha da mensagem segue Conventional Commits?"""
    if not isinstance(mensagem, str) or not mensagem.strip():
        return False
    return bool(_RE_CONVENTIONAL.match(mensagem.strip().splitlines()[0]))


def pct_conventional(commits: pd.DataFrame) -> float:
    """Proporção 0-1 dos commits que seguem Conventional Commits.

    Cada commit conta uma vez, mesmo que apareça em duas releases. NaN sem
    commits: zero diria "ninguém usa o padrão", e o fator estaria errado.
    """
    if commits.empty:
        return math.nan
    unicos = commits.drop_duplicates("sha") if "sha" in commits.columns else commits
    return float(unicos["mensagem"].map(e_conventional).mean())
