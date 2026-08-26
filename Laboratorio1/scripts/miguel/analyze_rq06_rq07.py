"""Gera os gráficos e o JSON de análise final de RQ06 e RQ07.

RQ06 (razão issues fechadas/total) e RQ07 (mergedPRs, releasesCount, tempo
desde pushedAt, agrupados por linguagem primária). A integridade dos dados
já foi validada em etapa anterior (scripts/miguel/validate_rq06_rq07_integrity.py) —
este script calcula métricas e visualiza, não repete checks de integridade.

RQ07 tem duas camadas: a descritiva (calcular_rq07 — mediana por linguagem,
o que os gráficos mostram) e a conclusiva (calcular_rq07_teste_hipotese — Mann-
Whitney U comparando linguagens populares vs. demais, para responder "recebem
mais X?" com significância estatística em vez de só "parece maior no
gráfico"). "Populares" aqui é o TOP_N_LINGUAGENS por nº de repositórios nesta
amostra (mesmo corte dos gráficos) — o repositório não tem uma lista externa
(ex. GitHub Octoverse) para usar como fonte oficial.

As colunas reais vêm de `coleta.py` (Laboratorio1/dados/repositorios.csv), que
não expõe um `totalIssues` bruto: é derivado aqui de issues_abertas +
issues_fechadas (ver COLS). Pelo mesmo motivo descrito no validador, `pushedAt`
usa `atualizado_em` (`updatedAt`) como proxy, já que a coleta não grava o
último push de código separadamente.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "repositorios.csv"
DEFAULT_OUTDIR = Path(__file__).resolve().parent.parent.parent / "dados" / "miguel" / "graficos"

# Mapeia os nomes lógicos (schema GraphQL original) para os nomes reais em
# dados/repositorios.csv. None = não existe como coluna bruta (ver docstring).
COLS: dict[str, str | None] = {
    "nameWithOwner": None,
    "primaryLanguage": "linguagem",
    "closedIssues": "issues_fechadas",
    "totalIssues": None,
    "mergedPRs": "prs_mergeadas",
    "releasesCount": "releases",
    "pushedAt": "atualizado_em",
}
# Necessária junto de closedIssues para derivar totalIssues = abertas + fechadas.
ISSUES_ABERTAS_COL = "issues_abertas"

REQUIRED_REAL_COLS = [v for v in COLS.values() if v] + [ISSUES_ABERTAS_COL]

HIST_BINS = 20
TOP_N_LINGUAGENS = 10
SEM_LINGUAGEM = "(no language)"

# Paleta (mesma linha visual de scripts/joao/graficos-joao.py), com fundo
# branco puro conforme pedido para este relatório.
COLOR_SURFACE = "#ffffff"
COLOR_PRIMARY_INK = "#0b0b0b"
COLOR_SECONDARY_INK = "#52514e"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_BLUE = "#2a78d6"
COLOR_ORANGE = "#eb6834"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "text.color": COLOR_PRIMARY_INK,
    "axes.edgecolor": COLOR_AXIS,
    "axes.labelcolor": COLOR_SECONDARY_INK,
    "xtick.color": COLOR_MUTED,
    "ytick.color": COLOR_MUTED,
    "figure.facecolor": COLOR_SURFACE,
    "axes.facecolor": COLOR_SURFACE,
    "savefig.facecolor": COLOR_SURFACE,
})


def _estilizar_eixo(ax: plt.Axes) -> None:
    """Remove bordas supérfluas e aplica grade leve (estilo do grupo)."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x" if ax.get_xlabel() == "" else "y", color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def carregar_dados(caminho: Path) -> pd.DataFrame:
    """Lê `caminho` como CSV; encerra com mensagem clara se ilegível ou sem as colunas do escopo."""
    try:
        df = pd.read_csv(caminho)
    except Exception as exc:  # noqa: BLE001 - qualquer falha de leitura vira mensagem clara
        print(f"Erro ao ler CSV '{caminho}': {exc}", file=sys.stderr)
        sys.exit(1)

    faltando = [c for c in REQUIRED_REAL_COLS if c not in df.columns]
    if faltando:
        print(
            f"Erro: colunas ausentes no CSV: {faltando}. Header encontrado: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return df


def calcular_rq06(df: pd.DataFrame) -> dict[str, Any]:
    """RQ06: closed_ratio = closedIssues / totalIssues, excluindo totalIssues == 0."""
    fechadas = pd.to_numeric(df[COLS["closedIssues"]], errors="coerce")
    abertas = pd.to_numeric(df[ISSUES_ABERTAS_COL], errors="coerce")
    total = abertas + fechadas

    validos = total > 0
    closed_ratio = (fechadas[validos] / total[validos]).reset_index(drop=True)
    counts, bin_edges = np.histogram(closed_ratio, bins=HIST_BINS, range=(0.0, 1.0))

    return {
        "closed_ratio": closed_ratio,
        "median": float(closed_ratio.median()),
        "mean": float(closed_ratio.mean()),
        "q1": float(closed_ratio.quantile(0.25)),
        "q3": float(closed_ratio.quantile(0.75)),
        "min": float(closed_ratio.min()),
        "max": float(closed_ratio.max()),
        "n_considerados": int(validos.sum()),
        "n_excluidos_zero_issues": int((~validos).sum()),
        "histogram": {"bins": bin_edges.tolist(), "counts": counts.tolist()},
    }


def _montar_trabalho_rq07(df: pd.DataFrame, agora: pd.Timestamp | None = None) -> pd.DataFrame:
    """Monta o DataFrame por repositório (linguagem, mergedPRs, releasesCount, dias_desde_push)
    usado tanto pela camada descritiva (calcular_rq07) quanto pela conclusiva
    (calcular_rq07_teste_hipotese)."""
    referencia = agora if agora is not None else pd.Timestamp.now(tz="UTC")

    linguagem = df[COLS["primaryLanguage"]].astype("object")
    linguagem = linguagem.where(linguagem.notna() & (linguagem.astype(str).str.strip() != ""), SEM_LINGUAGEM)

    pushed_at = pd.to_datetime(df[COLS["pushedAt"]], errors="coerce", utc=True)
    dias_desde_push = (referencia - pushed_at).dt.days

    return pd.DataFrame({
        "linguagem": linguagem,
        "mergedPRs": pd.to_numeric(df[COLS["mergedPRs"]], errors="coerce"),
        "releasesCount": pd.to_numeric(df[COLS["releasesCount"]], errors="coerce"),
        "dias_desde_push": dias_desde_push,
    })


def calcular_rq07(df: pd.DataFrame, agora: pd.Timestamp | None = None) -> list[dict[str, Any]]:
    """RQ07 (descritiva): mediana de mergedPRs, releasesCount e dias desde pushedAt, por primaryLanguage."""
    trabalho = _montar_trabalho_rq07(df, agora)

    resultado = [
        {
            "linguagem": grupo_nome,
            "n": int(len(grupo)),
            "mediana_prs": float(grupo["mergedPRs"].median()),
            "mediana_releases": float(grupo["releasesCount"].median()),
            "mediana_dias_push": float(grupo["dias_desde_push"].median()),
        }
        for grupo_nome, grupo in trabalho.groupby("linguagem")
    ]
    resultado.sort(key=lambda r: r["n"], reverse=True)
    return resultado


def calcular_rq07_teste_hipotese(
    df: pd.DataFrame,
    agora: pd.Timestamp | None = None,
    top_n: int = TOP_N_LINGUAGENS,
) -> dict[str, Any]:
    """RQ07 (conclusiva): Mann-Whitney U (linguagens populares vs. demais) para mergedPRs,
    releasesCount e dias_desde_push — transforma "parece maior no gráfico" em uma diferença
    estatisticamente significativa (ou não), com p-valor.

    "Populares" = TOP `top_n` linguagens por nº de repositórios nesta amostra (mesmo corte
    usado nos gráficos); repositórios sem linguagem detectada são excluídos do teste.
    """
    trabalho = _montar_trabalho_rq07(df, agora)
    trabalho = trabalho[trabalho["linguagem"] != SEM_LINGUAGEM]

    populares = set(trabalho["linguagem"].value_counts().head(top_n).index)
    eh_popular = trabalho["linguagem"].isin(populares)

    metricas: dict[str, Any] = {}
    for coluna in ("mergedPRs", "releasesCount", "dias_desde_push"):
        valores_populares = trabalho.loc[eh_popular, coluna].dropna()
        valores_demais = trabalho.loc[~eh_popular, coluna].dropna()
        estatistica, p_valor = mannwhitneyu(valores_populares, valores_demais, alternative="two-sided")
        metricas[coluna] = {
            "u_statistic": float(estatistica),
            "p_value": float(p_valor),
            "significativo_0_05": bool(p_valor < 0.05),
            "mediana_populares": float(valores_populares.median()),
            "mediana_demais": float(valores_demais.median()),
            "n_populares": int(len(valores_populares)),
            "n_demais": int(len(valores_demais)),
        }

    return {
        "top_n_linguagens_populares": top_n,
        "linguagens_populares": sorted(populares),
        "metricas": metricas,
    }


def plotar_rq06_hist(rq06: dict[str, Any], outdir: Path) -> Path:
    """Histograma de closed_ratio (RQ06) com a mediana anotada."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(rq06["closed_ratio"], bins=HIST_BINS, range=(0.0, 1.0), color=COLOR_BLUE,
             edgecolor=COLOR_SURFACE, linewidth=0.6, zorder=3)
    _estilizar_eixo(ax)
    ax.set_xlim(0, 1)

    ax.axvline(rq06["median"], color=COLOR_ORANGE, linewidth=1.8, linestyle="--", zorder=4)
    ax.text(
        rq06["median"], ax.get_ylim()[1] * 0.97, f"  mediana = {rq06['median']:.2f}",
        color=COLOR_ORANGE, fontsize=9.5, va="top", ha="left",
    )

    ax.set_xlabel("Razão de issues fechadas (closedIssues / totalIssues)")
    ax.set_ylabel("Número de repositórios")
    fig.suptitle("RQ06 — Distribuição da razão de issues fechadas", fontsize=14,
                 fontweight="bold", x=0.01, ha="left")
    ax.set_title(
        f"n={rq06['n_considerados']} repositórios considerados "
        f"({rq06['n_excluidos_zero_issues']} excluídos por totalIssues=0)",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    caminho = outdir / "rq06_hist.png"
    fig.savefig(caminho, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    return caminho


def plotar_rq06_box(rq06: dict[str, Any], outdir: Path) -> Path:
    """Boxplot de closed_ratio (RQ06), evidenciando outliers."""
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.boxplot(
        rq06["closed_ratio"], orientation="vertical", showfliers=True,
        boxprops=dict(color=COLOR_BLUE), medianprops=dict(color=COLOR_ORANGE, linewidth=1.8),
        whiskerprops=dict(color=COLOR_MUTED), capprops=dict(color=COLOR_MUTED),
        flierprops=dict(markeredgecolor=COLOR_MUTED, markersize=4),
    )
    ax.set_xticks([])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Razão de issues fechadas (closedIssues / totalIssues)")
    _estilizar_eixo(ax)

    fig.suptitle("RQ06 — Boxplot da razão de issues fechadas", fontsize=14,
                 fontweight="bold", x=0.02, ha="left")
    ax.set_title(
        f"n={rq06['n_considerados']} repositórios considerados "
        f"({rq06['n_excluidos_zero_issues']} excluídos por totalIssues=0)",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    caminho = outdir / "rq06_box.png"
    fig.savefig(caminho, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    return caminho


def _plotar_barras_rq07(
    rq07: list[dict[str, Any]],
    *,
    campo: str,
    titulo: str,
    subtitulo: str,
    rotulo_eixo: str,
    nome_arquivo: str,
    outdir: Path,
) -> Path:
    """Barras horizontais do TOP N linguagens por n, ordenadas por n decrescente."""
    top = rq07[:TOP_N_LINGUAGENS]
    top_para_plot = list(reversed(top))  # barh desenha de baixo pra cima
    rotulos = [f"{r['linguagem']} (n={r['n']})" for r in top_para_plot]
    valores = [r[campo] for r in top_para_plot]

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(rotulos, valores, color=COLOR_BLUE, zorder=3)
    _estilizar_eixo(ax)
    ax.set_xlabel(rotulo_eixo)

    fig.suptitle(titulo, fontsize=14, fontweight="bold", x=0.01, ha="left")
    ax.set_title(subtitulo, fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12)

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    caminho = outdir / nome_arquivo
    fig.savefig(caminho, dpi=150, facecolor=COLOR_SURFACE)
    plt.close(fig)
    return caminho


def plotar_rq07_prs(rq07: list[dict[str, Any]], outdir: Path) -> Path:
    return _plotar_barras_rq07(
        rq07,
        campo="mediana_prs",
        titulo="RQ07 — Contribuição (RQ02) por linguagem",
        subtitulo=f"Mediana de PRs mergeadas · top {TOP_N_LINGUAGENS} linguagens por nº de repositórios",
        rotulo_eixo="Mediana de PRs mergeadas",
        nome_arquivo="rq07_prs_por_linguagem.png",
        outdir=outdir,
    )


def plotar_rq07_releases(rq07: list[dict[str, Any]], outdir: Path) -> Path:
    return _plotar_barras_rq07(
        rq07,
        campo="mediana_releases",
        titulo="RQ07 — Releases (RQ03) por linguagem",
        subtitulo=f"Mediana de releases · top {TOP_N_LINGUAGENS} linguagens por nº de repositórios",
        rotulo_eixo="Mediana de releases",
        nome_arquivo="rq07_releases_por_linguagem.png",
        outdir=outdir,
    )


def plotar_rq07_atualizacao(rq07: list[dict[str, Any]], outdir: Path) -> Path:
    return _plotar_barras_rq07(
        rq07,
        campo="mediana_dias_push",
        titulo="RQ07 — Atualização (RQ04) por linguagem",
        subtitulo=f"Mediana de dias desde o último push · top {TOP_N_LINGUAGENS} linguagens por nº de repositórios",
        rotulo_eixo="Mediana de dias desde pushedAt (menor = mais recente)",
        nome_arquivo="rq07_atualizacao_por_linguagem.png",
        outdir=outdir,
    )


def exportar_analysis_data(
    rq06: dict[str, Any],
    rq07: list[dict[str, Any]],
    rq07_teste: dict[str, Any],
    outdir: Path,
) -> Path:
    """Grava analysis_data.json com os números exatos usados nos PNGs (fonte de verdade do dashboard)."""
    dados = {
        "rq06": {k: rq06[k] for k in (
            "median", "mean", "q1", "q3", "min", "max",
            "n_considerados", "n_excluidos_zero_issues", "histogram",
        )},
        "rq07": {"por_linguagem": rq07},
        "rq07_teste_hipotese": rq07_teste,
    }
    caminho = outdir / "analysis_data.json"
    caminho.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    return caminho


def gerar_analise(caminho_csv: Path, outdir: Path) -> list[Path]:
    """Lê `caminho_csv`, calcula RQ06/RQ07 e grava os 5 PNGs + analysis_data.json em `outdir`."""
    df = carregar_dados(caminho_csv)
    outdir.mkdir(parents=True, exist_ok=True)

    rq06 = calcular_rq06(df)
    rq07 = calcular_rq07(df)
    rq07_teste = calcular_rq07_teste_hipotese(df)

    caminhos = [
        plotar_rq06_hist(rq06, outdir),
        plotar_rq06_box(rq06, outdir),
        plotar_rq07_prs(rq07, outdir),
        plotar_rq07_releases(rq07, outdir),
        plotar_rq07_atualizacao(rq07, outdir),
        exportar_analysis_data(rq06, rq07, rq07_teste, outdir),
    ]
    return caminhos


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="Gera os gráficos e o JSON de análise final de RQ06 (issues fechadas) e RQ07 (PRs/releases/atualização por linguagem)."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_INPUT_PATH, help="Caminho do CSV de entrada")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="Diretório de saída dos gráficos/JSON")
    args = parser.parse_args(argv)

    for caminho in gerar_analise(args.csv, args.outdir):
        print(f"Gerado: {caminho}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
