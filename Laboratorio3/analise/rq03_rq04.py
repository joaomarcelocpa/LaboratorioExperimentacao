"""RQ 03 (CFR), RQ 04 (recuperação) e classificação DORA de referência (C1).

C1 = release como unidade de deploy, lead time (a), CFR (a): é a combinação
que alimenta as colunas `nota_*` e `classe_dora` do metricas.csv. A RQ 07
reaproveita `analise/saida/classificacao_c1.csv`.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analise import comum
from metricas.classificacao import classificar_metrica, classificar_repo

ORDEM = ["Elite", "High", "Medium", "Low"]
# métrica de classificar_metrica -> coluna de valor -> coluna de nota guardada
C1 = {
    "freq": ("freq_release", "nota_freq"),
    "lead_time": ("lt_release_h", "nota_lead_time"),
    "cfr": ("cfr_a", "nota_cfr"),
    "recuperacao": ("recuperacao_h", "nota_recuperacao"),
}


def reclassificar_c1(df: pd.DataFrame) -> pd.DataFrame:
    """Refaz as notas e a classe de cada repositório só a partir dos valores.

    Serve de conferência independente das colunas `nota_*` e `classe_dora` do
    metricas.csv: aplica a tabela de cortes do enunciado aos valores brutos.
    """
    saida = pd.DataFrame({"repo": df["repo"]})
    for nome, (valor, nota) in C1.items():
        saida[nota] = [classificar_metrica(nome, v) for v in df[valor]]
    classes = [classificar_repo([linha[n] for _, n in C1.values()])
               for _, linha in saida.iterrows()]
    saida["classe_dora"] = [c for c, _ in classes]
    saida["classe_dora_nota"] = [n for _, n in classes]
    return saida


def divergencias(df: pd.DataFrame, refeito: pd.DataFrame) -> int:
    """Quantos repositórios têm classe diferente entre o CSV e a reclassificação."""
    return int((df["classe_dora"].values != refeito["classe_dora"].values).sum())


def contagem_classes(df: pd.DataFrame) -> pd.DataFrame:
    c = df["classe_dora"].value_counts().reindex(ORDEM, fill_value=0)
    return pd.DataFrame({"classe": c.index, "repositorios": c.values,
                         "pct": c.values / c.sum()}).set_index("classe")


def tabela_rq03(df: pd.DataFrame) -> pd.DataFrame:
    return comum.tabela_resumo(df, ["cfr_a", "cfr_b"])


def tabela_rq04(df: pd.DataFrame) -> pd.DataFrame:
    """Recuperação em horas e a proporção de episódios censurados por repositório."""
    return comum.tabela_resumo(df, ["recuperacao_h", "pct_censurados"])


def figura_rq03(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, col, titulo in ((axes[0], "cfr_a", "(a) falha de CI"),
                            (axes[1], "cfr_b", "(b) release corretiva")):
        dados = df[col].dropna()
        ax.hist(dados, bins=np.linspace(0, 1, 21), color="#4C72B0", edgecolor="white")
        ax.axvline(dados.median(), color="#C44E52", linestyle="--",
                   label=f"mediana = {dados.median():.1%}")
        ax.set_xlabel("taxa de falha")
        ax.set_title(f"{titulo} (n = {len(dados)})")
        ax.legend()
    axes[0].set_ylabel("repositórios")
    fig.suptitle("RQ 03 · Change failure rate")
    fig.tight_layout()
    return fig


def figura_rq04(df: pd.DataFrame) -> plt.Figure:
    dados = df["recuperacao_h"].dropna()
    dados = dados[dados > 0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(dados, bins=np.logspace(np.log10(dados.min()), np.log10(dados.max()), 30),
            color="#4C72B0", edgecolor="white")
    ax.set_xscale("log")
    ax.axvline(dados.median(), color="#C44E52", linestyle="--",
               label=f"mediana = {dados.median():.1f} h")
    ax.set_xlabel("tempo de recuperação (horas, escala log)")
    ax.set_ylabel("repositórios")
    ax.set_title(f"RQ 04 · Tempo de recuperação (n = {len(dados)})")
    ax.legend()
    return fig


def figura_classes(contagem: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4.2))
    barras = ax.bar(contagem.index, contagem["repositorios"],
                    color=["#55A868", "#4C72B0", "#DD8452", "#C44E52"])
    for barra, pct in zip(barras, contagem["pct"]):
        ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height(),
                f"{int(barra.get_height())}\n({pct:.0%})", ha="center", va="bottom")
    ax.set_ylabel("repositórios")
    ax.set_title(f"Classificação DORA de referência (C1, n = {int(contagem['repositorios'].sum())})")
    ax.set_ylim(0, contagem["repositorios"].max() * 1.2)
    return fig


def main() -> None:
    df = comum.carregar_metricas()

    refeito = reclassificar_c1(df)
    diverge = divergencias(df, refeito)
    contagem = contagem_classes(df)

    # Primeiro a C1, que a RQ 07 espera.
    comum.salvar_tabela(refeito.set_index("repo"), "classificacao_c1")
    comum.salvar_tabela(contagem, "classes_dora_c1")

    rq03, rq04 = tabela_rq03(df), tabela_rq04(df)
    print("\n=== Classificação DORA de referência (C1) ===")
    print(contagem.to_string())
    print(f"Repositórios cuja classe difere da reclassificação independente: {diverge}")
    print("\n=== RQ 03 · CFR ===")
    print(rq03.to_string())
    print("\n=== RQ 04 · Recuperação (horas) e censura ===")
    print(rq04.to_string())

    comum.salvar_tabela(rq03, "rq03_cfr")
    comum.salvar_tabela(rq04, "rq04_recuperacao")
    comum.salvar_figura(figura_rq03(df), "rq03_histogramas")
    comum.salvar_figura(figura_rq04(df), "rq04_histograma")
    comum.salvar_figura(figura_classes(contagem), "classes_dora_c1")


if __name__ == "__main__":  # pragma: no cover
    main()
