"""G3 (erro tipo I por situação) e G4 (curvas de poder) a partir dos CSVs de Q1, Q2 e Q3."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.gerador import CORES_TESTE, FIGURES_DIR, ROTULOS_TESTE
from src.simulacao import SAIDA, margem_de_erro
from src.testes import ALFA

ROTULOS_SITUACAO = {
    "base": "Base\n(n = 30, σ = 2,52)",
    "cauda_mais_longa": "Cauda mais longa\n(n = 30, σ = 3,5)",
    "amostra_pequena": "Amostra pequena\n(n = 10, σ = 2,52)",
    "pequena_e_cauda_longa": "Pequena e cauda longa\n(n = 10, σ = 3,5)",
}


def carregar(pasta: Path = SAIDA) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Junta base (Q1 e Q2) e situações ruins (Q3) em tabelas com situacao, razao, teste e taxa."""
    q1 = pd.read_csv(pasta / "q1_erro_tipo_i.csv")
    q2 = pd.read_csv(pasta / "q2_poder.csv")
    q3 = pd.read_csv(pasta / "q3_situacoes.csv")
    base = q2.rename(columns={"poder": "taxa"}).assign(situacao="base")
    todas = pd.concat([base, q3], ignore_index=True)
    erro = pd.concat(
        [
            q1.rename(columns={"erro_tipo_i": "taxa"}).assign(situacao="base")[
                ["situacao", "teste", "taxa"]
            ],
            q3[q3["razao_medianas"] == 1.0][["situacao", "teste", "taxa"]],
        ],
        ignore_index=True,
    )
    return erro, todas


def plotar_g3(erro: pd.DataFrame, destino: Path = FIGURES_DIR) -> Path:
    """Barras do erro tipo I (%) de cada teste por situação, com linha em 5%."""
    destino.mkdir(parents=True, exist_ok=True)
    situacoes = [s for s in ROTULOS_SITUACAO if s in set(erro["situacao"])]
    x = np.arange(len(situacoes))
    largura = 0.36

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, teste in enumerate(ROTULOS_TESTE):
        taxas = [
            erro[(erro["situacao"] == s) & (erro["teste"] == teste)]["taxa"].iloc[0]
            for s in situacoes
        ]
        barras = ax.bar(
            x + (i - 0.5) * largura, np.array(taxas) * 100, largura,
            yerr=[margem_de_erro(t) * 100 for t in taxas], capsize=3,
            color=CORES_TESTE[teste], label=ROTULOS_TESTE[teste],
        )
        ax.bar_label(barras, fmt="%.1f%%", padding=4, fontsize=9)

    ax.axhline(ALFA * 100, color="black", linestyle="--", linewidth=1.2, label="Nível nominal (5%)")
    ax.set_xticks(x, [ROTULOS_SITUACAO[s] for s in situacoes], fontsize=9)
    ax.set_title("G3 — Erro tipo I dos dois testes em cada situação simulada (H₀ verdadeira)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Situação simulada", fontsize=10)
    ax.set_ylabel("Rejeições de H₀ (%)", fontsize=10)
    ax.set_ylim(0, 7)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    caminho = destino / "g3_erro_tipo_i.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho


def plotar_g4(todas: pd.DataFrame, destino: Path = FIGURES_DIR) -> Path:
    """Curvas de poder (%) × razão de medianas, uma por teste, em um painel por situação."""
    destino.mkdir(parents=True, exist_ok=True)
    situacoes = [s for s in ROTULOS_SITUACAO if s in set(todas["situacao"])]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    fig.suptitle("G4 — Curvas de poder dos dois testes", fontsize=13, fontweight="bold")
    for ax, situacao in zip(axes.flat, situacoes):
        dados = todas[todas["situacao"] == situacao]
        for teste in ROTULOS_TESTE:
            d = dados[dados["teste"] == teste].sort_values("razao_medianas")
            ax.errorbar(
                d["razao_medianas"], d["taxa"] * 100,
                yerr=[margem_de_erro(t) * 100 for t in d["taxa"]], marker="o", capsize=3,
                color=CORES_TESTE[teste], linewidth=2, label=ROTULOS_TESTE[teste],
            )
        ax.axhline(ALFA * 100, color="black", linestyle="--", linewidth=1, label="Nível nominal (5%)")
        ax.set_title(ROTULOS_SITUACAO[situacao].replace("\n", " "), fontsize=10)
        ax.grid(alpha=0.3)
    for ax in axes[1]:
        ax.set_xlabel("Razão das medianas (grupo B ÷ grupo A, adimensional)", fontsize=9)
    for ax in axes[:, 0]:
        ax.set_ylabel("Poder: rejeições de H₀ (%)", fontsize=9)
    axes[0, 0].legend(fontsize=9, loc="upper left")
    fig.tight_layout()

    caminho = destino / "g4_curvas_de_poder.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho


if __name__ == "__main__":
    erro, todas = carregar()
    print(f"G3 salvo em: {plotar_g3(erro)}")
    print(f"G4 salvo em: {plotar_g4(todas)}")
