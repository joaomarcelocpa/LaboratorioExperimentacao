import csv
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "repositorios.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "dados" / "joao" / "graficos"

# Data de referência usada em rqs-hipoteses.md para calcular a idade dos repositórios.
REFERENCE_DATE = datetime(2026, 8, 18, tzinfo=timezone.utc)

# Paleta (skill de dataviz — instância validada, modo claro).
COLOR_SURFACE = "#fcfcfb"
COLOR_PRIMARY_INK = "#0b0b0b"
COLOR_SECONDARY_INK = "#52514e"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_BLUE = "#2a78d6"
COLOR_ORANGE = "#eb6834"
COLOR_RED = "#e34948"

plt.rcParams.update(
    {
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
    }
)


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


def carregar_dados(input_path=DEFAULT_INPUT_PATH):
    with open(input_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    idades_anos, prs, releases = [], [], []
    for row in rows:
        criado_em = _parse_criado_em(row.get("criado_em", ""))
        if criado_em is not None:
            idades_anos.append((REFERENCE_DATE - criado_em).days / 365.25)

        prs_v = _parse_numeric(row.get("prs_mergeadas", ""))
        if prs_v is not None:
            prs.append(prs_v)

        releases_v = _parse_numeric(row.get("releases", ""))
        if releases_v is not None:
            releases.append(releases_v)

    return idades_anos, prs, releases


def _limites_iqr(values):
    """Mesmo método de scripts/joao/validador-joao.py (IQR, 1.5x)."""
    ordered = sorted(values)
    n = len(ordered)
    q1 = statistics.median(ordered[: n // 2])
    q3 = statistics.median(ordered[(n + 1) // 2 :])
    iqr = q3 - q1
    return q1, q3, q1 - 1.5 * iqr, q3 + 1.5 * iqr


def _estilizar_eixo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="y", color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def _rodape(fig, n_amostra):
    fig.text(
        0.01,
        0.005,
        f"Fonte: dados/repositorios.csv (n={n_amostra}) · Metodologia: scripts/joao/validador-joao.py",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
    )


def plot_rq01_idade(idades_anos, output_dir):
    mediana = statistics.median(idades_anos)
    media = statistics.mean(idades_anos)
    limiar_hipotese = 8.0

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(
        idades_anos,
        bins=30,
        color=COLOR_BLUE,
        edgecolor=COLOR_SURFACE,
        linewidth=0.6,
        zorder=3,
    )
    _estilizar_eixo(ax)

    ax.axvline(mediana, color=COLOR_PRIMARY_INK, linewidth=1.8, zorder=4)
    ax.axvline(media, color=COLOR_SECONDARY_INK, linewidth=1.4, linestyle="--", zorder=4)
    ax.axvline(limiar_hipotese, color=COLOR_ORANGE, linewidth=1.4, linestyle=":", zorder=4)

    legenda = (
        f"— mediana: {mediana:.1f} anos\n"
        f"-- média: {media:.1f} anos\n"
        f"·· hipótese: {limiar_hipotese:.0f} anos"
    )
    ax.text(
        0.985, 0.97, legenda, transform=ax.transAxes, fontsize=9.5,
        ha="right", va="top", linespacing=1.7,
        bbox=dict(boxstyle="round,pad=0.45", facecolor=COLOR_SURFACE, edgecolor=COLOR_GRID),
    )

    ax.set_xlabel("Idade do repositório (anos)")
    ax.set_ylabel("Nº de repositórios")
    fig.suptitle("RQ01 — Repositórios populares são maduros?", fontsize=14,
                 fontweight="bold", x=0.01, ha="left")
    ax.set_title(
        "Distribuição da idade (criado_em) vs. limiar de 8 anos da hipótese",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    _rodape(fig, len(idades_anos))
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    caminho = output_dir / "rq01_idade_repositorios.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    return caminho


def _teto_legivel(valor):
    """Arredonda `valor` para cima até um número redondo, fácil de ler no eixo."""
    if valor <= 10:
        return math.ceil(valor)
    magnitude = 10 ** (len(str(int(valor))) - 1)
    passo = magnitude / 2
    return math.ceil(valor / passo) * passo


def plot_distribuicao_assimetrica(values, titulo, subtitulo, rotulo_eixo, caminho_saida, n_total):
    mediana = statistics.median(values)
    media = statistics.mean(values)
    q1, q3, limite_inf, limite_sup = _limites_iqr(values)
    outliers = sorted(v for v in values if v < limite_inf or v > limite_sup)

    teto = _teto_legivel(limite_sup)
    visiveis = [v for v in values if v <= teto]
    n_ocultos = len(values) - len(visiveis)

    fig, ax = plt.subplots(figsize=(9, 5.8))
    ax.hist(
        visiveis,
        bins=25,
        color=COLOR_BLUE,
        edgecolor=COLOR_SURFACE,
        linewidth=0.6,
        zorder=3,
    )
    _estilizar_eixo(ax)
    ax.set_xlim(0, teto)

    ax.axvline(mediana, color=COLOR_PRIMARY_INK, linewidth=1.8, zorder=4)
    ax.axvline(media, color=COLOR_SECONDARY_INK, linewidth=1.4, linestyle="--", zorder=4)

    legenda = (
        f"— mediana: {mediana:.0f}\n"
        f"-- média: {media:.0f}\n\n"
        f"{len(outliers)} outliers (IQR)\n"
        f"acima de {limite_sup:.0f}, até {outliers[-1]:.0f}\n"
        f"({n_ocultos} fora do gráfico abaixo)"
    )
    ax.text(
        0.985, 0.97, legenda, transform=ax.transAxes, fontsize=9.5,
        ha="right", va="top", linespacing=1.7,
        bbox=dict(boxstyle="round,pad=0.45", facecolor=COLOR_SURFACE, edgecolor=COLOR_GRID),
    )

    ax.set_xlabel(rotulo_eixo)
    ax.set_ylabel("Nº de repositórios")
    fig.suptitle(titulo, fontsize=14, fontweight="bold", x=0.01, ha="left")
    ax.set_title(
        f"{subtitulo} · eixo truncado em {teto:.0f} para manter a leitura",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    _rodape(fig, n_total)
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho_saida, dpi=160)
    plt.close(fig)
    return caminho_saida


def plot_rq02_prs(prs, output_dir):
    return plot_distribuicao_assimetrica(
        prs,
        titulo="RQ02 — Repositórios populares recebem muitas contribuições aceitas?",
        subtitulo="Distribuição de PRs mergeadas por repositório",
        rotulo_eixo="PRs mergeadas",
        caminho_saida=output_dir / "rq02_prs_mergeadas.png",
        n_total=len(prs),
    )


def plot_rq03_releases(releases, output_dir):
    return plot_distribuicao_assimetrica(
        releases,
        titulo="RQ03 — Repositórios populares têm releases frequentes?",
        subtitulo="Distribuição de releases por repositório",
        rotulo_eixo="Releases",
        caminho_saida=output_dir / "rq03_releases.png",
        n_total=len(releases),
    )


def gerar_graficos(input_path=DEFAULT_INPUT_PATH, output_dir=DEFAULT_OUTPUT_DIR):
    idades_anos, prs, releases = carregar_dados(input_path)
    caminhos = [
        plot_rq01_idade(idades_anos, output_dir),
        plot_rq02_prs(prs, output_dir),
        plot_rq03_releases(releases, output_dir),
    ]
    return caminhos


if __name__ == "__main__":
    for caminho in gerar_graficos():
        print(f"Gráfico salvo em {caminho}")
