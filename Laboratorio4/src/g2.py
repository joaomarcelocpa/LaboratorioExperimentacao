"""G2: distribuição do t de Welch sob H0, região de rejeição e p-valor."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from src.gerador import FIGURES_DIR, gerar_dados
from src.testes import ALFA, aplicar_testes

COR_WELCH = "#2E7D32"
COR_REJEICAO = "#C62828"


def plotar_g2(t_obs: float, gl: float, destino: Path = FIGURES_DIR) -> Path:
    """Salva G2 para a estatística t_obs com gl graus de liberdade."""
    destino.mkdir(parents=True, exist_ok=True)
    dist = stats.t(gl)
    t_crit = dist.ppf(1 - ALFA / 2)
    p_valor = 2 * dist.sf(abs(t_obs))

    x = np.linspace(-4.5, 4.5, 800)
    y = dist.pdf(x)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, y, color=COR_WELCH, linewidth=2, label=f"t de Welch sob H₀ (gl = {gl:.1f})")

    ax.fill_between(
        x, y, where=(x <= -t_crit) | (x >= t_crit),
        color=COR_REJEICAO, alpha=0.35,
        label=f"Região de rejeição (α = {ALFA:.2f}, duas caudas de {ALFA / 2:.3f})",
    )
    ax.fill_between(
        x, y, where=(x <= -abs(t_obs)) | (x >= abs(t_obs)),
        facecolor="none", edgecolor="black", hatch="///", linewidth=0,
        label=f"p-valor = {p_valor:.3f} (área em |t| ≥ {abs(t_obs):.2f})",
    )

    for v in (-t_crit, t_crit):
        ax.axvline(v, color=COR_REJEICAO, linestyle="--", linewidth=1)
    ax.axvline(t_obs, color="black", linewidth=1.5)
    ax.annotate(
        f"t observado = {t_obs:.2f}", xy=(t_obs, dist.pdf(t_obs)),
        xytext=(t_obs - 0.2, dist.pdf(0) * 0.6), ha="right", fontsize=10,
        arrowprops={"arrowstyle": "->"},
    )
    ax.text(t_crit, dist.pdf(0) * 0.35, f"t crítico = ±{t_crit:.2f}",
            ha="left", fontsize=9, color=COR_REJEICAO)

    ax.set_title("G2 — Estatística t de Welch sob H₀: região de rejeição e p-valor",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Estatística t de Welch (adimensional)", fontsize=10)
    ax.set_ylabel("Densidade de probabilidade", fontsize=10)
    ax.set_ylim(top=dist.pdf(0) * 1.3)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3)

    caminho = destino / "g2_regiao_rejeicao.png"
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return caminho


if __name__ == "__main__":
    dados = gerar_dados(seed=42)
    r = aplicar_testes(dados["com_bot"], dados["sem_bot"])
    print(f"G2 salvo em: {plotar_g2(r['welch']['t'], r['welch']['gl'])}")
