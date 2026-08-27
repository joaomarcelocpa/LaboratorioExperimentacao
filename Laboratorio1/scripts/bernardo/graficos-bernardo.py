import csv
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "repositorios.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "dados" / "bernardo" / "graficos"

REFERENCE_DATE = datetime(2026, 8, 26, tzinfo=timezone.utc)

COLOR_SURFACE = "#fcfcfb"
COLOR_PRIMARY_INK = "#0b0b0b"
COLOR_SECONDARY_INK = "#52514e"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"
COLOR_AXIS = "#c3c2b7"
COLOR_BLUE = "#2a78d6"
COLOR_ORANGE = "#eb6834"

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


def carregar_dados(input_path=DEFAULT_INPUT_PATH):
    with open(input_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    dias_atualizacao, linguagens = [], []
    for row in rows:
        raw = row.get("atualizado_em", "")
        if raw and raw.strip():
            try:
                dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                dias_atualizacao.append((REFERENCE_DATE - dt).total_seconds() / 86400)
            except ValueError:
                pass

        lang = row.get("linguagem", "").strip()
        linguagens.append(lang if lang else "(sem linguagem)")

    return dias_atualizacao, linguagens


def _limites_iqr(values):
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
        f"Fonte: dados/repositorios.csv (n={n_amostra}) · Metodologia: scripts/bernardo/validador-bernardo.py",
        fontsize=8,
        color=COLOR_MUTED,
        ha="left",
    )


def plot_rq04_atualizacao(dias, output_dir):
    mediana = statistics.median(dias)
    media = statistics.mean(dias)
    minimo, maximo = min(dias), max(dias)
    _, _, _, limite_sup = _limites_iqr(dias)
    outliers = [v for v in dias if v > limite_sup]
    limiar_hipotese = 30

    # A amostra inteira cai bem abaixo da hipótese de 30 dias: `atualizado_em`
    # é o `updatedAt` do GitHub (proxy de `pushedAt`, que a coleta não grava —
    # ver scripts/miguel/analyze_rq06_rq07.py), e essa coleta ocorreu numa
    # janela de poucos dias, então o intervalo observado é naturalmente
    # estreito. Por isso o eixo foca no intervalo real dos dados em vez de
    # começar em zero ou truncar cauda longa — aqui não há uma.
    amplitude = maximo - minimo
    margem = max(amplitude * 0.08, 0.15)
    x_min = max(0, minimo - margem)
    x_max = maximo + margem

    largura_bin = max(amplitude / 40, 0.02)
    n_bins = max(10, math.ceil((x_max - x_min) / largura_bin))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.hist(dias, bins=n_bins, range=(x_min, x_max), color=COLOR_BLUE,
            edgecolor=COLOR_SURFACE, linewidth=0.6, zorder=3)
    _estilizar_eixo(ax)
    ax.set_xlim(x_min, x_max)
    ax.xaxis.set_major_formatter(lambda v, _pos: f"{v:.1f}")

    ax.axvline(mediana, color=COLOR_PRIMARY_INK, linewidth=1.8, zorder=4)
    ax.axvline(media, color=COLOR_SECONDARY_INK, linewidth=1.4, linestyle="--", zorder=4)

    legenda_linhas = [
        f"— mediana: {mediana:.2f} dias",
        f"-- média: {media:.2f} dias",
        f"min–máx: {minimo:.2f}–{maximo:.2f} dias",
        "",
        f"{len(outliers)} outliers (IQR)",
        f"hipótese ({limiar_hipotese} dias): folga ampla",
    ]

    ax.text(
        0.985, 0.97, "\n".join(legenda_linhas), transform=ax.transAxes, fontsize=9.5,
        ha="right", va="top", linespacing=1.7,
        bbox=dict(boxstyle="round,pad=0.45", facecolor=COLOR_SURFACE, edgecolor=COLOR_GRID),
    )

    ax.set_xlabel("Dias desde a última atualização (atualizado_em)")
    ax.set_ylabel("Nº de repositórios")
    fig.suptitle("RQ04 — Repositórios populares são atualizados com frequência?",
                 fontsize=14, fontweight="bold", x=0.01, ha="left")
    ax.set_title(
        f"Distribuição de dias desde atualizado_em · amostra entre "
        f"{minimo:.1f} e {maximo:.1f} dias (limiar da hipótese: {limiar_hipotese} dias)",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    fig.text(
        0.01, 0.055,
        "Nota: atualizado_em é o campo updatedAt do GitHub (proxy de pushedAt — a coleta não grava o último push\n"
        "separadamente) e ocorreu numa janela curta, então o intervalo observado aqui é naturalmente estreito.",
        fontsize=7.5, color=COLOR_MUTED, ha="left", linespacing=1.4,
    )
    _rodape(fig, len(dias))
    fig.tight_layout(rect=(0, 0.11, 1, 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    caminho = output_dir / "rq04_atualizacao.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    return caminho


def plot_rq05_linguagens(linguagens, output_dir, top_n=15):
    counter = Counter(linguagens)
    total = len(linguagens)
    top = counter.most_common(top_n)
    nomes = [lang for lang, _ in reversed(top)]
    contagens = [count for _, count in reversed(top)]
    percentuais = [count / total * 100 for count in contagens]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    bars = ax.barh(nomes, contagens, color=COLOR_BLUE, edgecolor=COLOR_SURFACE, linewidth=0.5, zorder=3)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.grid(axis="x", color=COLOR_GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)

    for bar, pct in zip(bars, percentuais):
        ax.text(
            bar.get_width() + total * 0.003,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.1f}%",
            va="center", fontsize=9, color=COLOR_SECONDARY_INK,
        )

    ax.set_xlabel("Nº de repositórios")
    fig.suptitle("RQ05 — Repositórios populares usam as linguagens mais populares?",
                 fontsize=14, fontweight="bold", x=0.01, ha="left")
    ax.set_title(
        f"Top {top_n} linguagens primárias entre os 1000 repositórios mais estrelados",
        fontsize=10.5, color=COLOR_SECONDARY_INK, loc="left", pad=12,
    )

    _rodape(fig, total)
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    caminho = output_dir / "rq05_linguagens.png"
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    return caminho


def gerar_graficos(input_path=DEFAULT_INPUT_PATH, output_dir=DEFAULT_OUTPUT_DIR):
    dias_atualizacao, linguagens = carregar_dados(input_path)
    caminhos = [
        plot_rq04_atualizacao(dias_atualizacao, output_dir),
        plot_rq05_linguagens(linguagens, output_dir),
    ]
    return caminhos


if __name__ == "__main__":
    for caminho in gerar_graficos():
        print(f"Gráfico salvo em {caminho}")
