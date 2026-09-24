"""Gera dashboard.html (raiz do repo) a partir dos dados já consolidados e analisados.

Mesmo padrão do Lab 1 (scripts/dashboard/gerar-dashboard.py): o HTML final é
montado a partir de três peças, todas em scripts/dashboard/:
  - dashboard-template.html: página estática (HTML/JS) com dois placeholders,
    "__TRIALS_DATA__" (os 12 trials, um registro por linha de
    dados_consolidados.csv) e "__ANALISE_DATA__" (RQ1/RQ2/RQ3 já calculados
    por analise_estatistica.py — o dashboard só exibe esses números, não os
    recalcula), e um <link> para dashboard.css.
  - dashboard.css: estilos do dashboard (mesmo sistema de design do Lab 1,
    com paleta própria e os tokens --manual/--ia para os dois tratamentos).
  - resultados/dados_consolidados.csv e resultados/analise_estatistica.json:
    saída de consolidar_dados.py e analise_estatistica.py, respectivamente
    (rode os dois antes deste script).

Uso:
    cd scripts
    python consolidar_dados.py
    python analise_estatistica.py
    python dashboard/gerar-dashboard.py
"""

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TRIALS_PATH = REPO_ROOT / "resultados" / "dados_consolidados.csv"
DEFAULT_ANALISE_PATH = REPO_ROOT / "resultados" / "analise_estatistica.json"
DEFAULT_TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard-template.html"
DEFAULT_CSS_PATH = Path(__file__).resolve().parent / "dashboard.css"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dashboard.html"

PLACEHOLDER_TRIALS = "__TRIALS_DATA__"
PLACEHOLDER_ANALISE = "__ANALISE_DATA__"
CSS_LINK_TAG = '<link rel="stylesheet" href="dashboard.css">'

_CAMPOS_NUMERICOS = {
    "numero_leetcode", "tempo_segundos", "testes_passados", "testes_total",
    "taxa_sucesso", "cc_media", "mi", "loc", "sloc", "duplicacao_pct",
}


def _parse_valor(chave: str, valor: str):
    if chave in _CAMPOS_NUMERICOS:
        return float(valor) if "." in valor else int(valor)
    if chave == "censurado":
        return valor == "True"
    return valor


def carregar_trials(path: Path = DEFAULT_TRIALS_PATH) -> dict:
    with path.open(encoding="utf-8") as f:
        linhas = [
            {chave: _parse_valor(chave, valor) for chave, valor in row.items()}
            for row in csv.DictReader(f)
        ]
    return {"n": len(linhas), "trials": linhas}


def carregar_analise(path: Path = DEFAULT_ANALISE_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(
            f"Erro: {path} não encontrado. Rode consolidar_dados.py e "
            "analise_estatistica.py antes de gerar o dashboard.",
            file=sys.stderr,
        )
        sys.exit(1)


def gerar_dashboard(
    trials_path=DEFAULT_TRIALS_PATH,
    analise_path=DEFAULT_ANALISE_PATH,
    template_path=DEFAULT_TEMPLATE_PATH,
    css_path=DEFAULT_CSS_PATH,
    output_path=DEFAULT_OUTPUT_PATH,
):
    trials = carregar_trials(trials_path)
    analise = carregar_analise(analise_path)

    template = template_path.read_text(encoding="utf-8")
    for placeholder, path in (
        (PLACEHOLDER_TRIALS, template_path),
        (PLACEHOLDER_ANALISE, template_path),
    ):
        if placeholder not in template:
            raise ValueError(f"Placeholder {placeholder!r} não encontrado em {path}")
    if CSS_LINK_TAG not in template:
        raise ValueError(f"Tag {CSS_LINK_TAG!r} não encontrada em {template_path}")

    css = css_path.read_text(encoding="utf-8")
    html = template.replace(CSS_LINK_TAG, f"<style>\n{css}</style>")
    html = html.replace(PLACEHOLDER_TRIALS, json.dumps(trials, ensure_ascii=False))
    html = html.replace(PLACEHOLDER_ANALISE, json.dumps(analise, ensure_ascii=False))
    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    caminho = gerar_dashboard()
    print(f"Dashboard gerado em {caminho}")
