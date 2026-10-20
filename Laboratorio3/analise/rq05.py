"""RQ 05: correlação de Spearman entre frequência de deploy e CFR."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats


def correlacao_spearman(x: pd.Series, y: pd.Series) -> dict:
    """Correlação de Spearman entre x e y, descartando pares com NaN.

    Retorna dict com 'rho', 'pvalue', 'n'.
    """
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(df)
    if n < 3:
        return {"rho": float("nan"), "pvalue": float("nan"), "n": n}
    result = stats.spearmanr(df["x"], df["y"])
    return {"rho": float(result.statistic), "pvalue": float(result.pvalue), "n": n}


def tabela_correlacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela de correlações Spearman entre freq_release e cada variante de CFR."""
    linhas = []
    for variante in ("cfr_a", "cfr_b"):
        r = correlacao_spearman(df["freq_release"], df[variante])
        linhas.append({
            "variante": variante,
            "rho": round(r["rho"], 4),
            "pvalue": round(r["pvalue"], 4),
            "n": r["n"],
            "significativo": r["pvalue"] < 0.05,
        })
    return pd.DataFrame(linhas)


def scatter_freq_cfr(
    df: pd.DataFrame,
    variante: str,
    rho: float,
    pvalue: float,
    caminho_saida: Path,
) -> None:
    """Salva scatter plot freq_release × variante com escala log e anotação ρ/p."""
    import matplotlib.pyplot as plt

    pares = df[["freq_release", variante]].dropna()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(pares["freq_release"], pares[variante], alpha=0.5, s=20)
    ax.set_xscale("log")
    ax.set_xlabel("Frequência de releases (releases/semana) — escala log")
    ax.set_ylabel(f"CFR ({variante})")
    ax.set_title(
        f"RQ05 · freq_release × {variante}\n"
        f"ρ = {rho:.3f}  p = {pvalue:.4f}  n = {len(pares)}"
    )
    fig.tight_layout()
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho_saida, dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    raiz = Path(__file__).parent.parent
    df = pd.read_csv(raiz / "data/processed/metricas.csv")

    tabela = tabela_correlacoes(df)
    print("\n=== RQ 05 · Correlação Spearman: freq_release × CFR ===")
    print(tabela.to_string(index=False))

    saida = raiz / "data/analise"
    for _, row in tabela.iterrows():
        scatter_freq_cfr(
            df,
            variante=row["variante"],
            rho=row["rho"],
            pvalue=row["pvalue"],
            caminho_saida=saida / f"rq05_scatter_{row['variante']}.png",
        )
    print(f"\nPlots salvos em {saida}/")
