"""Tags com a data do commit, em consultas GraphQL de 100 em 100.

Pela REST, cada tag custa uma chamada a /commits/{sha} só para ler a data: em
repositórios com centenas de tags isso era 80% a 93% de todas as chamadas da
coleta. O GraphQL devolve o commit de cada tag junto da listagem.

A data é a mesma do caminho REST (`commit.author.date`): `authoredDate`.
"""
from __future__ import annotations

import logging

from coleta import http

_log = logging.getLogger(__name__)

# Uma tag anotada aponta para um objeto Tag, que aponta para o commit; tags de
# tags existem, mas são raras. Três níveis cobrem o que se vê na prática.
_COMMIT = "... on Commit { oid authoredDate }"
_NIVEL3 = f"target {{ __typename {_COMMIT} }}"
_NIVEL2 = f"target {{ __typename {_COMMIT} ... on Tag {{ {_NIVEL3} }} }}"
CONSULTA = f"""
query($dono: String!, $nome: String!, $depois: String) {{
  repository(owner: $dono, name: $nome) {{
    refs(refPrefix: "refs/tags/", first: 100, after: $depois) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{
        name
        target {{ __typename {_COMMIT} ... on Tag {{ {_NIVEL2} }} }}
      }}
    }}
  }}
}}
"""


def _commit_da_tag(alvo: dict | None) -> dict | None:
    """Desce pelas tags anotadas até o commit."""
    while alvo is not None:
        if alvo.get("__typename") == "Commit":
            return alvo
        alvo = alvo.get("target")
    return None


def tags_com_data(repo: str) -> list[dict] | None:
    """Linhas de tags.csv (sem `repo`) de todas as tags, ou None.

    None quer dizer "o GraphQL não achou o repositório" (renomeado, por
    exemplo): quem chama cai no caminho REST, que segue o redirecionamento.
    Qualquer outro erro do GraphQL estoura, porque devolver uma lista parcial
    de tags mudaria freq_tag sem ninguém ver.
    """
    dono, nome = repo.split("/", 1)
    linhas: list[dict] = []
    cursor: str | None = None

    while True:
        resposta = http.graphql(CONSULTA, {"dono": dono, "nome": nome, "depois": cursor})
        erros = resposta.get("errors") or []
        dados = resposta.get("data") or {}
        if dados.get("repository") is None:
            if all(e.get("type") == "NOT_FOUND" for e in erros) or not erros:
                return None
            raise http.ErroDeHTTP(f"GraphQL {repo}: {erros[0].get('message')}", 200)
        if erros:
            raise http.ErroDeHTTP(f"GraphQL {repo}: {erros[0].get('message')}", 200)

        refs = dados["repository"]["refs"]
        for no in refs["nodes"]:
            commit = _commit_da_tag(no.get("target"))
            if commit is None:
                _log.warning("%s: tag %r não aponta para um commit; ignorada", repo, no["name"])
                continue
            linhas.append({
                "repo": repo,
                "tag": no["name"],
                "sha": commit["oid"],
                "data_commit": commit["authoredDate"],
            })

        if not refs["pageInfo"]["hasNextPage"]:
            return linhas
        cursor = refs["pageInfo"]["endCursor"]
