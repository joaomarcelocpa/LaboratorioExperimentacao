"""
Dashboard de Visualização — Lab 2, Sprint 3, Passo 6.

Gera gráficos (Pandas + Matplotlib/Seaborn) comparando tempo, taxa de sucesso
e métricas estáticas entre os tratamentos manual e com IA, a partir de
resultados/dados_consolidados.csv (gerado por consolidar_dados.py).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from consolidar_dados import carregar_trials

RAIZ = Path(__file__).parent.parent
SAIDA = RAIZ / "resultados" / "graficos"

PALETA = {"manual": "#4C72B0", "ia": "#DD8452"}
ROTULOS = {"manual": "Manual", "ia": "Com IA"}

sns.set_theme(style="whitegrid")


def _preparar_df() -> pd.DataFrame:
    df = pd.DataFrame(carregar_trials())
    df["tempo_min"] = df["tempo_segundos"] / 60
    df["tratamento_label"] = df["tratamento"].map(ROTULOS)
    return df


def _boxplot_com_pontos(df: pd.DataFrame, campo: str, titulo: str, ylabel: str, arquivo: str):
    fig, ax = plt.subplots(figsize=(6, 5))
    ordem = ["manual", "ia"]
    sns.boxplot(
        data=df, x="tratamento", y=campo, order=ordem,
        hue="tratamento", palette=PALETA, legend=False, width=0.5, ax=ax,
    )
    sns.stripplot(
        data=df, x="tratamento", y=campo, order=ordem,
        color="black", size=6, alpha=0.6, jitter=0.08, ax=ax,
    )
    ax.set_xticks(range(len(ordem)))
    ax.set_xticklabels([ROTULOS[t] for t in ordem])
    ax.set_xlabel("Tratamento")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=150)
    plt.close(fig)


def _slope_por_kata(df: pd.DataFrame, campo: str, titulo: str, ylabel: str, arquivo: str, log=False):
    """Uma linha por kata ligando o valor manual ao valor com IA - evidencia o
    pareamento por kata usado no teste de Wilcoxon."""
    fig, ax = plt.subplots(figsize=(6, 5))
    pivot = df.pivot(index="kata_id", columns="tratamento", values=campo)
    for kata_id, row in pivot.iterrows():
        ax.plot([0, 1], [row["manual"], row["ia"]], marker="o", color="gray", alpha=0.7)
        ax.annotate(kata_id, (0, row["manual"]), textcoords="offset points", xytext=(-12, 0), fontsize=9)

    ax.scatter([0] * len(pivot), pivot["manual"], color=PALETA["manual"], zorder=3, label="Manual")
    ax.scatter([1] * len(pivot), pivot["ia"], color=PALETA["ia"], zorder=3, label="Com IA")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Manual", "Com IA"])
    ax.set_xlim(-0.3, 1.3)
    if log:
        ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.legend()
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=150)
    plt.close(fig)


def _barras_mediana(df: pd.DataFrame, campo: str, titulo: str, ylabel: str, arquivo: str, ylim=None):
    fig, ax = plt.subplots(figsize=(6, 5))
    medianas = df.groupby("tratamento")[campo].median().reindex(["manual", "ia"])
    ax.bar(
        [ROTULOS[t] for t in medianas.index], medianas.values,
        color=[PALETA[t] for t in medianas.index],
    )
    for i, v in enumerate(medianas.values):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    if ylim:
        ax.set_ylim(*ylim)
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=150)
    plt.close(fig)


def gerar_graficos(df: pd.DataFrame):
    SAIDA.mkdir(parents=True, exist_ok=True)

    # RQ1 - Tempo
    _boxplot_com_pontos(
        df, "tempo_min", "RQ1 - Tempo até passar nos testes (por tratamento)",
        "Tempo (minutos)", "rq1_tempo_boxplot.png",
    )
    _slope_por_kata(
        df, "tempo_segundos", "RQ1 - Tempo por kata (manual vs. com IA)",
        "Tempo (segundos, escala log)", "rq1_tempo_por_kata.png", log=True,
    )

    # RQ2 - Taxa de sucesso
    _barras_mediana(
        df, "taxa_sucesso", "RQ2 - Taxa de sucesso mediana dos testes de aceitação",
        "Taxa de sucesso (%)", "rq2_taxa_sucesso.png",
    )

    # RQ3 - Estrutura do código
    _boxplot_com_pontos(
        df, "cc_media", "RQ3 - Complexidade ciclomática média (Radon cc)",
        "Complexidade ciclomática média", "rq3_complexidade.png",
    )
    _boxplot_com_pontos(
        df, "mi", "RQ3 - Índice de manutenibilidade (Radon mi)",
        "Índice de manutenibilidade (MI)", "rq3_manutenibilidade.png",
    )
    _boxplot_com_pontos(
        df, "loc", "RQ3 - LOC (métrica de controle)",
        "Linhas de código (LOC)", "rq3_loc.png",
    )
    _barras_mediana(
        df, "duplicacao_pct", "RQ3 - Duplicação de código mediana",
        "Duplicação (%)", "rq3_duplicacao.png", ylim=(0, 5),
    )

    # Painel único consolidando as 3 RQs
    fig, eixos = plt.subplots(2, 3, figsize=(16, 9))
    especificacoes = [
        ("tempo_min", "RQ1 - Tempo (min)", "Tempo (min)"),
        ("taxa_sucesso", "RQ2 - Taxa de sucesso (%)", "Taxa de sucesso (%)"),
        ("cc_media", "RQ3 - Complexidade ciclomática", "CC média"),
        ("mi", "RQ3 - Manutenibilidade (MI)", "MI"),
        ("loc", "RQ3 - LOC (controle)", "LOC"),
        ("duplicacao_pct", "RQ3 - Duplicação (%)", "Duplicação (%)"),
    ]
    for ax, (campo, titulo, ylabel) in zip(eixos.flat, especificacoes):
        sns.boxplot(
            data=df, x="tratamento", y=campo, order=["manual", "ia"],
            hue="tratamento", palette=PALETA, legend=False, width=0.5, ax=ax,
        )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Manual", "Com IA"])
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_title(titulo, fontsize=11)
        if campo == "taxa_sucesso":
            ax.set_ylim(0, 110)
        if campo == "duplicacao_pct":
            ax.set_ylim(-0.5, 5)
    fig.suptitle("Dashboard — Assistentes de IA vs. Codificação Manual (Lab 2)", fontsize=14)
    fig.tight_layout()
    fig.savefig(SAIDA / "dashboard_consolidado.png", dpi=150)
    plt.close(fig)

    _painel_halstead(df)
    _painel_loc(df)


def _painel_loc(df: pd.DataFrame):
    """LOC por tipo (além da especificação, que só pede LOC total como controle):
    boxplots de cada categoria + composição mediana empilhada por tratamento."""
    fig, eixos = plt.subplots(2, 3, figsize=(16, 9))
    especificacoes = [
        ("ncloc", "NCLOC (total - branco - comentário)", "NCLOC"),
        ("loc_branco", "LOC em branco", "Linhas em branco"),
        ("loc_comentario", "LOC comentário", "Linhas de comentário"),
        ("loc_diretivas", "LOC diretivas (import)", "Diretivas"),
        ("loc_decl", "LOC declarativas", "Declarativas"),
        ("loc_exec", "LOC executáveis", "Executáveis"),
    ]
    for ax, (campo, titulo, ylabel) in zip(eixos.flat, especificacoes):
        sns.boxplot(
            data=df, x="tratamento", y=campo, order=["manual", "ia"],
            hue="tratamento", palette=PALETA, legend=False, width=0.5, ax=ax,
        )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Manual", "Com IA"])
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_title(titulo, fontsize=11)
        if campo == "loc_comentario":
            ax.set_ylim(-0.5, 5)
    fig.suptitle("Aprofundamento — LOC por tipo (além da especificação)", fontsize=14)
    fig.tight_layout()
    fig.savefig(SAIDA / "aprofundamento_loc.png", dpi=150)
    plt.close(fig)

    # Composição mediana empilhada: onde exatamente a IA "economiza" linhas.
    medianas = df.groupby("tratamento")[["loc_diretivas", "loc_decl", "loc_exec", "loc_branco"]].median()
    medianas = medianas.reindex(["manual", "ia"])
    categorias = [
        ("loc_diretivas", "Diretivas", "#8172B2"),
        ("loc_decl", "Declarativas", "#55A868"),
        ("loc_exec", "Executáveis", "#C44E52"),
        ("loc_branco", "Em branco", "#B0B0B0"),
    ]
    fig, ax = plt.subplots(figsize=(6, 5))
    base = [0, 0]
    for campo, rotulo, cor in categorias:
        valores = medianas[campo].values
        ax.bar([ROTULOS[t] for t in medianas.index], valores, bottom=base, label=rotulo, color=cor)
        base = [b + v for b, v in zip(base, valores)]
    ax.set_ylabel("LOC (mediana)")
    ax.set_title("Composição mediana do LOC por tratamento")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(SAIDA / "aprofundamento_loc_composicao.png", dpi=150)
    plt.close(fig)


def _painel_halstead(df: pd.DataFrame):
    """Métricas além do que a especificação pede para RQ3: Halstead (já coletado
    desde a Sprint 1, mas não usado antes desta sprint)."""
    fig, eixos = plt.subplots(2, 2, figsize=(11, 9))
    especificacoes = [
        ("hal_volume", "Halstead - Volume", "Volume"),
        ("hal_dificuldade", "Halstead - Dificuldade", "Dificuldade"),
        ("hal_esforco", "Halstead - Esforço", "Esforço"),
        ("hal_bugs_estimados", "Halstead - Bugs estimados", "Bugs estimados"),
    ]
    for ax, (campo, titulo, ylabel) in zip(eixos.flat, especificacoes):
        sns.boxplot(
            data=df, x="tratamento", y=campo, order=["manual", "ia"],
            hue="tratamento", palette=PALETA, legend=False, width=0.5, ax=ax,
        )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Manual", "Com IA"])
        ax.set_xlabel("")
        ax.set_ylabel(ylabel)
        ax.set_title(titulo, fontsize=11)
    fig.suptitle("Aprofundamento — Métricas de Halstead (além da especificação)", fontsize=14)
    fig.tight_layout()
    fig.savefig(SAIDA / "aprofundamento_halstead.png", dpi=150)
    plt.close(fig)


def main():
    df = _preparar_df()
    gerar_graficos(df)
    print(f"Gráficos salvos em {SAIDA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
