"""Gera dashboard.html (raiz do repo) a partir de dados/repositorios.csv.

Dashboard compartilhado por todas as RQs do grupo (não só as do João) — o
HTML é montado a partir de três peças, todas em scripts/dashboard/:
  - dashboard-template.html: página estática (HTML/JS) com um placeholder
    "__REPOS_DATA__" onde os dados entram e um <link> para dashboard.css.
  - dashboard.css: estilos do dashboard, editável à parte para manter o
    template legível; é inlinado num <style> no HTML final.
  - dados/repositorios.csv: fonte dos dados, exportada aqui como JSON compacto
    (um registro por repositório) e injetada no lugar do placeholder.

Para complementar o dashboard com outras RQs, edite dashboard-template.html
(e dashboard.css, se precisar de estilos novos) — os dados de cada
repositório (autor, repo, estrelas, idade, prs, releases) já ficam
disponíveis no array `REPOS.repos` dentro do HTML gerado; cada integrante
pode consumir os mesmos campos ou estender o JSON aqui embaixo com colunas
adicionais do CSV para sua(s) RQ(s).
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_INPUT_PATH = REPO_ROOT / "dados" / "repositorios.csv"
DEFAULT_TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard-template.html"
DEFAULT_CSS_PATH = Path(__file__).resolve().parent / "dashboard.css"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dashboard.html"

# Data de referência usada para calcular a idade dos repositórios (ver rqs-hipoteses.md).
REFERENCE_DATE = datetime(2026, 8, 18, tzinfo=timezone.utc)

PLACEHOLDER = "__REPOS_DATA__"
CSS_LINK_TAG = '<link rel="stylesheet" href="dashboard.css">'


def _parse_criado_em(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_numeric(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None


def extrair_repos(input_path=DEFAULT_INPUT_PATH):
    with open(input_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    repos = []
    for row in rows:
        criado_em = _parse_criado_em(row.get("criado_em", ""))
        idade = round((REFERENCE_DATE - criado_em).days / 365.25, 3) if criado_em else None
        repos.append(
            {
                "autor": row.get("autor", ""),
                "repo": row.get("nome_repositorio", ""),
                "estrelas": _parse_numeric(row.get("estrelas", "")),
                "idade": idade,
                "prs": _parse_numeric(row.get("prs_mergeadas", "")),
                "releases": _parse_numeric(row.get("releases", "")),
            }
        )
    return repos


def gerar_dashboard(
    input_path=DEFAULT_INPUT_PATH,
    template_path=DEFAULT_TEMPLATE_PATH,
    css_path=DEFAULT_CSS_PATH,
    output_path=DEFAULT_OUTPUT_PATH,
):
    repos = extrair_repos(input_path)
    payload = json.dumps({"n": len(repos), "repos": repos}, ensure_ascii=False)

    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"Placeholder {PLACEHOLDER!r} não encontrado em {template_path}")
    if CSS_LINK_TAG not in template:
        raise ValueError(f"Tag {CSS_LINK_TAG!r} não encontrada em {template_path}")

    css = css_path.read_text(encoding="utf-8")
    html = template.replace(CSS_LINK_TAG, f"<style>\n{css}</style>")
    html = html.replace(PLACEHOLDER, payload)
    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    caminho = gerar_dashboard()
    print(f"Dashboard gerado em {caminho}")
