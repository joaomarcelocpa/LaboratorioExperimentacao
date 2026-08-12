import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

_SEARCH_REPOS_QUERY = """
query($first: Int!, $after: String) {
  search(
    query: "stars:>1 sort:stars-desc"
    type: REPOSITORY
    first: $first
    after: $after
  ) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        name
        nameWithOwner
        stargazerCount
        createdAt
        updatedAt
        primaryLanguage {
          name
        }
      }
    }
  }
}
"""

_STATS_BATCH_SIZE = 10


def _build_stats_query(name_with_owners: list[str]) -> str:
    parts = ["query {"]
    for i, nwo in enumerate(name_with_owners):
        owner, name = nwo.split("/", 1)
        parts.append(f"""
  r{i}: repository(owner: "{owner}", name: "{name}") {{
    mergedPullRequests: pullRequests(states: MERGED) {{ totalCount }}
    releases {{ totalCount }}
    openIssues: issues(states: OPEN) {{ totalCount }}
    closedIssues: issues(states: CLOSED) {{ totalCount }}
  }}""")
    parts.append("\n}")
    return "".join(parts)


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não está definida. Configure um .env a partir de .env.example."
        )
    return token


def run_graphql_query(query: str, variables: dict, token: str | None = None) -> dict:
    token = token or get_github_token()
    for attempt in range(4):
        response = requests.post(
            GITHUB_GRAPHQL_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query, "variables": variables},
        )
        if response.status_code in (502, 503):
            time.sleep(2 ** attempt)
            continue
        break

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


def fetch_top_repositories(count: int = 100, token: str | None = None) -> list[dict]:
    repositories: list[dict] = []
    after: str | None = None

    while len(repositories) < count:
        batch = min(100, count - len(repositories))
        data = run_graphql_query(
            _SEARCH_REPOS_QUERY,
            {"first": batch, "after": after},
            token=token,
        )
        search = data["search"]

        for node in search["nodes"]:
            if len(repositories) >= count:
                break
            repositories.append({
                "name": node["name"],
                "nameWithOwner": node["nameWithOwner"],
                "stargazerCount": node["stargazerCount"],
                "createdAt": node["createdAt"],
                "updatedAt": node["updatedAt"],
                "primaryLanguage": (
                    node["primaryLanguage"]["name"]
                    if node["primaryLanguage"]
                    else None
                ),
            })

        if not search["pageInfo"]["hasNextPage"]:
            break
        after = search["pageInfo"]["endCursor"]

    for i in range(0, len(repositories), _STATS_BATCH_SIZE):
        batch = repositories[i : i + _STATS_BATCH_SIZE]
        query = _build_stats_query([r["nameWithOwner"] for r in batch])
        stats_data = run_graphql_query(query, {}, token=token)

        for j, repo in enumerate(batch):
            stats = stats_data[f"r{j}"]
            repo["mergedPullRequestsCount"] = stats["mergedPullRequests"]["totalCount"]
            repo["releasesCount"] = stats["releases"]["totalCount"]
            repo["openIssuesCount"] = stats["openIssues"]["totalCount"]
            repo["closedIssuesCount"] = stats["closedIssues"]["totalCount"]

    return repositories


# TODO implementar save_to_csv(repositories: list[dict], path: str) -> None
# usando apenas a stdlib (módulo csv — sem pandas ou bibliotecas externas).
#
# Entrada: lista de dicts retornada por fetch_top_repositories(), cada um com as chaves:
#   name, nameWithOwner, stargazerCount, createdAt, updatedAt, primaryLanguage,
#   mergedPullRequestsCount, releasesCount, openIssuesCount, closedIssuesCount
#
# Saída esperada: arquivo CSV com cabeçalho na primeira linha e uma linha por repositório,
# separador vírgula, encoding UTF-8. Exemplo de uso:
#   repos = fetch_top_repositories(count=100)
#   save_to_csv(repos, "data/repositorios.csv")
#
# Observação: primaryLanguage pode ser None; gravar string vazia nesses casos.


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()

    login = check_connection()
    console.print(f"[bold green]✓[/bold green] Conectado como [cyan bold]{login}[/cyan bold]\n")

    with console.status("[bold yellow]Coletando 100 repositórios mais populares do GitHub...[/bold yellow]"):
        repos = fetch_top_repositories(count=100)

    console.print(f"[bold green]✓[/bold green] [bold]{len(repos)}[/bold] repositórios coletados\n")

    table = Table(title="Top 100 Repositórios GitHub por Estrelas", show_lines=True)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Repositório", min_width=35)
    table.add_column("⭐ Estrelas", justify="right", style="yellow")
    table.add_column("Linguagem", min_width=12)
    table.add_column("PRs Mergeadas", justify="right", style="green")
    table.add_column("Releases", justify="right", style="blue")
    table.add_column("Issues ✓/Total", justify="right")

    for i, repo in enumerate(repos, 1):
        total_issues = repo["openIssuesCount"] + repo["closedIssuesCount"]
        ratio = f"{repo['closedIssuesCount']}/{total_issues}" if total_issues > 0 else "—"
        table.add_row(
            str(i),
            repo["nameWithOwner"],
            f"{repo['stargazerCount']:,}",
            repo["primaryLanguage"] or "—",
            f"{repo['mergedPullRequestsCount']:,}",
            str(repo["releasesCount"]),
            ratio,
        )

    console.print(table)
