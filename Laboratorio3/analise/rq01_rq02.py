"""RQ 01 (frequência de deploy) e RQ 02 (lead time): mediana, IQR e figuras."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analise import comum

HORAS_POR_DIA = 24.0


def tabela_rq01(df: pd.DataFrame) -> pd.DataFrame:
    """Frequência de release (por semana): n, mediana, q1, q3 e iqr."""
    return comum.tabela_resumo(df, ["freq_release"])


def tabela_rq02(df: pd.DataFrame) -> pd.DataFrame:
    """Lead time das duas variantes, em horas e em dias."""
    t = comum.tabela_resumo(df, ["lt_release_h", "lt_commit_h"])
    for col in ("mediana", "q1", "q3", "iqr"):
        t[f"{col}_dias"] = t[col] / HORAS_POR_DIA
    return t


def comparar_variantes(df: pd.DataFrame) -> dict:
    """Quantos repositórios têm a variante (a) maior que a (b), e a razão das medianas.

    A (a) usa o commit mais antigo da release; a (b), a mediana de todos os
    commits. Por isso a (a) tende a ser maior: um commit antigo a puxa para
    cima e quase não mexe na (b).
    """
    pares = df[["lt_release_h", "lt_commit_h"]].dropna()
    return {
        "n": int(len(pares)),
        "a_maior_que_b": int((pares["lt_release_h"] > pares["lt_commit_h"]).sum()),
        "pct_a_maior_que_b": float((pares["lt_release_h"] > pares["lt_commit_h"]).mean()),
        "razao_medianas_a_b": float(pares["lt_release_h"].median() / pares["lt_commit_h"].median()),
    }


def faixas_frequencia(df: pd.DataFrame) -> pd.DataFrame:
    """Quantos repositórios caem em cada faixa DORA de frequência."""
    nota = df["nota_freq"].dropna().astype(int)
    nomes = {4: "Elite (≥ 7/sem)", 3: "High (1 a 7/sem)", 2: "Medium (1/mês a 1/sem)", 1: "Low (< 1/mês)"}
    contagem = nota.value_counts().reindex([4, 3, 2, 1], fill_value=0)
    return pd.DataFrame({"faixa": [nomes[n] for n in contagem.index],
                         "repositorios": contagem.values,
                         "pct": contagem.values / contagem.sum()})


def figura_rq01(df: pd.DataFrame) -> plt.Figure:
    dados = df["freq_release"].dropna()
    dados = dados[dados > 0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(dados, bins=np.logspace(np.log10(dados.min()), np.log10(dados.max()), 30),
            color="#4C72B0", edgecolor="white")
    ax.set_xscale("log")
    ax.axvline(dados.median(), color="#C44E52", linestyle="--",
               label=f"mediana = {dados.median():.2f}/semana")
    ax.set_xlabel("releases por semana (escala log)")
    ax.set_ylabel("repositórios")
    ax.set_title(f"RQ 01 · Frequência de release (n = {len(dados)})")
    ax.legend()
    return fig


def figura_rq02(df: pd.DataFrame) -> plt.Figure:
    pares = df[["lt_release_h", "lt_commit_h"]].dropna() / HORAS_POR_DIA
    pares = pares[(pares > 0).all(axis=1)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    ax1.boxplot([pares["lt_release_h"], pares["lt_commit_h"]],
                tick_labels=["(a) por release", "(b) por commit"], showfliers=True)
    ax1.set_yscale("log")
    ax1.set_ylabel("lead time (dias, escala log)")
    ax1.set_title("Distribuição das duas variantes")
    ax2.scatter(pares["lt_commit_h"], pares["lt_release_h"], s=14, alpha=0.6, color="#4C72B0")
    limites = [min(pares.min()), max(pares.max())]
    ax2.plot(limites, limites, color="#C44E52", linestyle="--", label="(a) = (b)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("(b) por commit (dias)")
    ax2.set_ylabel("(a) por release (dias)")
    ax2.set_title("Cada ponto é um repositório")
    ax2.legend()
    fig.suptitle(f"RQ 02 · Lead time (n = {len(pares)})")
    fig.tight_layout()
    return fig


def main() -> None:
    df = comum.carregar_metricas()

    rq01 = tabela_rq01(df)
    rq02 = tabela_rq02(df)
    faixas = faixas_frequencia(df)
    comparacao = comparar_variantes(df)

    print("\n=== RQ 01 · Frequência de release (por semana) ===")
    print(rq01.to_string())
    print("\nFaixas DORA de frequência:")
    print(faixas.to_string(index=False))
    print("\n=== RQ 02 · Lead time (horas e dias) ===")
    print(rq02.to_string())
    print("\n(a) vs (b):", comparacao)

    comum.salvar_tabela(rq01, "rq01_frequencia")
    comum.salvar_tabela(faixas.set_index("faixa"), "rq01_faixas")
    comum.salvar_tabela(rq02, "rq02_lead_time")
    comum.salvar_tabela(pd.DataFrame([comparacao]), "rq02_variantes")
    comum.salvar_figura(figura_rq01(df), "rq01_histograma")
    comum.salvar_figura(figura_rq02(df), "rq02_variantes")


if __name__ == "__main__":  # pragma: no cover
    main()
