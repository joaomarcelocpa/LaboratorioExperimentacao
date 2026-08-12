import os

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não está definida. Configure um .env a partir de .env.example."
        )
    return token


def run_graphql_query(query: str, variables: dict, token: str | None = None) -> dict:
    token = token or get_github_token()
    response = requests.post(
        GITHUB_GRAPHQL_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "variables": variables},
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Requisição falhou com status {response.status_code}: {response.text}"
        )

    body = response.json()
    if "errors" in body:
        raise RuntimeError(f"API do GitHub retornou erros: {body['errors']}")

    return body["data"]


def check_connection(token: str | None = None) -> str:
    data = run_graphql_query("query { viewer { login } }", {}, token=token)
    return data["viewer"]["login"]


# TODO (issue "Sprint 1 - Extrair dados dos 100 repositórios com mais estrelas do
# GitHub"): implementar fetch_top_repositories(count: int = 100) usando
# run_graphql_query com a query completa dos 9 campos mapeados às RQs.
# Ver docs/superpowers/specs/2026-08-11-lab01-github-coleta-design.md para a
# query GraphQL, o mapeamento de campos e o formato de saída esperado.


if __name__ == "__main__":
    login = check_connection()
    print(f"Conexão com a API do GitHub OK. Autenticado como: {login}")
