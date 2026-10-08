"""Deployments de produção com o estado final, em consultas GraphQL de 100.

Pela REST, cada deployment custa uma chamada a /deployments/{id}/statuses só
para ler o estado mais recente: um repositório com 446 deployments gastou 446
chamadas, 36% de toda a coleta de uma rodada de 10 repositórios. O GraphQL
traz o último status junto da listagem.

Os campos são os mesmos do caminho REST: `id`, `environment`, `created_at`,
`sha` e o estado do status mais recente (em minúsculas, como a REST).
"""
from __future__ import annotations

from coleta import http

CONSULTA = """
query($dono: String!, $nome: String!, $ambientes: [String!], $depois: String) {
  repository(owner: $dono, name: $nome) {
    deployments(environments: $ambientes, first: 100, after: $depois,
                orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        databaseId
        environment
        createdAt
        commit { oid }
        latestStatus { state }
      }
    }
  }
}
"""


def deployments_com_estado(repo: str, ambientes: list[str]) -> list[dict] | None:
    """Linhas de deployments.csv dos ambientes pedidos, ou None.

    None quer dizer "o GraphQL não achou o repositório" (renomeado, por
    exemplo): quem chama cai no caminho REST, que segue o redirecionamento.
    Qualquer outro erro estoura, porque uma lista parcial de deployments
    mudaria freq_deploy sem ninguém ver.

    Sem status, o estado é "desconhecido", como na REST.
    """
    if not ambientes:
        return []
    dono, nome = repo.split("/", 1)
    linhas: list[dict] = []
    cursor: str | None = None

    while True:
        resposta = http.graphql(
            CONSULTA,
            {"dono": dono, "nome": nome, "ambientes": ambientes, "depois": cursor},
        )
        erros = resposta.get("errors") or []
        dados = resposta.get("data") or {}
        if dados.get("repository") is None:
            if all(e.get("type") == "NOT_FOUND" for e in erros) or not erros:
                return None
            raise http.ErroDeHTTP(f"GraphQL {repo}: {erros[0].get('message')}", 200)
        if erros:
            raise http.ErroDeHTTP(f"GraphQL {repo}: {erros[0].get('message')}", 200)

        deployments = dados["repository"]["deployments"]
        for no in deployments["nodes"]:
            status = no.get("latestStatus")
            linhas.append({
                "repo": repo,
                "id": no["databaseId"],
                "environment": no["environment"],
                "criado_em": no["createdAt"],
                "sha": (no.get("commit") or {}).get("oid", ""),
                "estado_final": status["state"].lower() if status else "desconhecido",
            })

        if not deployments["pageInfo"]["hasNextPage"]:
            return linhas
        cursor = deployments["pageInfo"]["endCursor"]
