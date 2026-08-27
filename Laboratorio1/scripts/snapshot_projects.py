"""Exporta um snapshot do GitHub Projects (v2) do grupo para CSV.

Reaproveita a infraestrutura de consulta GraphQL de `coleta.py` (token via
GITHUB_TOKEN, retry para 502/503/504), mas aponta para o schema de
ProjectV2 em vez do schema de repositórios: para cada item do board, grava
o número/título da Issue, o valor atual do campo Status (coluna), os
assignees e a URL.

Rodar ao final de cada sprint (Lab01S01, S02, S03...) e acumular a saída no
mesmo CSV (--append, padrão), já que o GitHub Projects não expõe histórico
de mudança de coluna via API: essa série de snapshots é o que reconstrói a
evolução do board sprint a sprint, usada como base de dados pelos Labs 04 e
05.

Exemplo de uso:
    python scripts/snapshot_projects.py --login joaomarcelocpa --numero 2 --sprint Lab01S03
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent / "dados" / "kanban" / "snapshots_projects.csv"

CSV_HEADER = [
    "sprint",
    "data_snapshot",
    "issue_numero",
    "titulo",
    "status",
    "assignees",
    "url",
]

_PROJECT_ITEMS_QUERY = """
query($login: String!, $numero: Int!, $after: String) {
  user(login: $login) {
    projectV2(number: $numero) {
      items(first: 50, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          content {
            ... on Issue {
              number
              title
              url
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
          }
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não está definida. Configure um .env"
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
        if response.status_code in (502, 503, 504):
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


def _status_from_field_values(field_values: list[dict]) -> str:
    for field_value in field_values:
        field = field_value.get("field") or {}
        if field.get("name") == "Status":
            return field_value.get("name") or ""
    return ""


def fetch_project_items(login: str, numero: int, token: str | None = None) -> list[dict]:
    items: list[dict] = []
    after: str | None = None

    while True:
        data = run_graphql_query(
            _PROJECT_ITEMS_QUERY,
            {"login": login, "numero": numero, "after": after},
            token=token,
        )
        project = data["user"]["projectV2"]
        page = project["items"]

        for node in page["nodes"]:
            content = node.get("content")
            if not content:
                continue
            assignees = ";".join(
                a["login"] for a in content.get("assignees", {}).get("nodes", [])
            )
            items.append({
                "issue_numero": content["number"],
                "titulo": content["title"],
                "url": content["url"],
                "status": _status_from_field_values(node.get("fieldValues", {}).get("nodes", [])),
                "assignees": assignees,
            })

        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]

    return items


def save_snapshot_to_csv(items: list[dict], sprint: str, path: Path, append: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not (append and path.exists())
    mode = "a" if append and path.exists() else "w"
    snapshot_dt = datetime.now(timezone.utc).isoformat()

    with open(path, mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(CSV_HEADER)
        for item in items:
            writer.writerow([
                sprint,
                snapshot_dt,
                item["issue_numero"],
                item["titulo"],
                item["status"],
                item["assignees"],
                item["url"],
            ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exporta um snapshot do GitHub Projects (v2) do grupo para CSV."
    )
    parser.add_argument("--login", required=True, help="Login do dono do Project (ex.: joaomarcelocpa)")
    parser.add_argument("--numero", type=int, required=True, help="Número do Project (v2), ex.: 2")
    parser.add_argument("--sprint", required=True, help="Rótulo da sprint (ex.: Lab01S03)")
    parser.add_argument("--output", type=Path, default=DEFAULT_CSV_PATH, help="Caminho do CSV acumulado de snapshots")
    parser.add_argument("--no-append", action="store_true", help="Sobrescreve o CSV em vez de acumular")
    args = parser.parse_args(argv)

    items = fetch_project_items(args.login, args.numero)
    save_snapshot_to_csv(items, args.sprint, args.output, append=not args.no_append)

    print(f"Snapshot da sprint '{args.sprint}': {len(items)} item(ns) gravado(s) em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
