"""Gerador de dados simulados (lognormal) e gráfico G1."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PARAMS = {
    "com_bot": {"mu": 1.616, "sigma": 2.374, "n": 30},
    "sem_bot": {"mu": 2.638, "sigma": 2.671, "n": 30},
}

CORES = {"com_bot": "#2196F3", "sem_bot": "#FF9800"}

ROTULOS = {"com_bot": "Com bot", "sem_bot": "Sem bot"}

FIGURES_DIR = Path(__file__).parent.parent / "results" / "figures"


def gerar_dados(seed: int = 42) -> dict[str, np.ndarray]:
    """Gera os dois grupos lognormais com semente fixa."""
    rng = np.random.default_rng(seed)
    return {
        grupo: rng.lognormal(mean=p["mu"], sigma=p["sigma"], size=p["n"])
        for grupo, p in PARAMS.items()
    }


def plotar_g1(
    dados_reais: pd.DataFrame,
    dados_simulados: dict[str, np.ndarray],
    destino: Path = FIGURES_DIR,
) -> Path:
    """Salva G1 (histogramas reais × simulados) em destino."""
    destino.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        "G1 — Tempo até o merge: dados reais × simulados",
        fontsize=13,
        fontweight="bold",
    )

    fontes = [
        ("Dados reais", {
            g: dados_reais[dados_reais["grupo"] == g]["horas_ate_merge"].values
            for g in PARAMS
        }),
        ("Dados simulados", dados_simulados),
    ]

    for ax, (titulo, fonte) in zip(axes, fontes):
        for grupo, valores in fonte.items():
            # Escala log para lidar com a cauda longa da lognormal
            ax.hist(
                np.log1p(valores),
                bins=15,
                alpha=0.55,
                color=CORES[grupo],
                label=ROTULOS[grupo],
                edgecolor="white",
                linewidth=0.5,
            )
        ax.set_title(titulo, fontsize=11)
        ax.set_xlabel("log(1 + horas até merge)  [h]", fontsize=10)
        ax.set_ylabel("Frequência", fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    caminho = destino / "g1_dados_reais_vs_simulados.png"
    plt.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close()
    return caminho


if __name__ == "__main__":
    raiz = Path(__file__).parent.parent
    dados_reais = pd.read_csv(raiz / "data" / "raw" / "prs.csv")
    dados_simulados = gerar_dados()
    caminho = plotar_g1(dados_reais, dados_simulados)
    print(f"G1 salvo em: {caminho}")
