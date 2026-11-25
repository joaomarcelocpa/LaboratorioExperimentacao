"""Gráficos da análise (issues #123 e #125). Todos com eixos rotulados e unidades.

Média por modo com IC 95% (média ± 1,96 erro-padrão entre cadeias); traços
individuais por cadeia onde a issue pede. Nenhum índice composto.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis import descritiva

CORES = {"incremental": "#c0392b", "regenerado": "#2c6fbb"}
MARCADORES = {"cabe": "o", "tensiona": "s"}
PASSOS = list(range(0, 11))


def _salvar(fig, caminho: Path) -> None:
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def _media_ic(valores: pd.Series) -> tuple[float, float]:
    v = valores.dropna().astype(float)
    if len(v) == 0:
        return np.nan, np.nan
    meia = 1.96 * v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
    return float(v.mean()), float(meia)


def _linha_media(ax, d: pd.DataFrame, coluna: str, modo: str, rotulo: str | None = None, **kw) -> None:
    passos, medias, meias = [], [], []
    for passo, g in d.groupby("step"):
        m, h = _media_ic(g[coluna])
        passos.append(passo); medias.append(m); meias.append(h)
    passos, medias, meias = map(np.asarray, (passos, medias, meias))
    ax.plot(passos, medias, marker="o", color=CORES[modo], label=rotulo or modo, **kw)
    ax.fill_between(passos, medias - meias, medias + meias, color=CORES[modo], alpha=0.15)


def regressao_por_cadeia(df: pd.DataFrame, caminho: Path) -> None:
    """Regressão acumulada por passo: um traço por cadeia e a média por modo.

    A suíte de regressão acumula os testes de todos os pedidos aceitos, então a
    fração que falha no passo n já é o estado acumulado até ali.
    """
    d = df[df["status"] == "ok"].copy()
    d["taxa"] = 100 * d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    fig, eixos = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, (modo, g) in zip(eixos, d.groupby("mode")):
        for _, c in g.groupby("chain_id"):
            ax.plot(c["step"], c["taxa"], color=CORES[modo], alpha=0.25, lw=0.8)
        _linha_media(ax, g, "taxa", modo, rotulo=f"média ({g['chain_id'].nunique()} cadeias)", lw=2.2)
        ax.set_title(modo); ax.set_xlabel("passo"); ax.set_xticks(PASSOS); ax.grid(alpha=0.3); ax.legend(loc="upper left")
    eixos[0].set_ylabel(descritiva.UNIDADES["taxa_regressao"])
    _salvar(fig, caminho)


def regressao_acumulada(df: pd.DataFrame, caminho: Path) -> None:
    """Fração das cadeias que já regrediram em algum passo até n, por modo."""
    t = descritiva.regressao_acumulada(df)
    fig, ax = plt.subplots(figsize=(6, 4))
    for modo, g in t.groupby("mode"):
        ax.plot(g["step"], 100 * g["regressao_acumulada"], marker="o", color=CORES[modo], label=modo)
    ax.set_xlabel("passo"); ax.set_xticks(PASSOS); ax.set_ylim(-2, 102)
    ax.set_ylabel("% das cadeias com ao menos uma regressão até o passo"); ax.grid(alpha=0.3); ax.legend()
    _salvar(fig, caminho)


def estrutura_por_passo(df: pd.DataFrame, caminho: Path) -> None:
    """Violações, localidade (arquivos e módulos tocados) e duplicação por passo."""
    d = df[df["status"] == "ok"]
    paineis = ("arch_violations", "files_touched", "modules_touched", "dup_pct")
    fig, eixos = plt.subplots(2, 2, figsize=(10, 7))
    for ax, metrica in zip(eixos.flat, paineis):
        base = d if metrica in ("arch_violations", "dup_pct") else d[d["step"] >= 1]
        for modo, g in base.groupby("mode"):
            _linha_media(ax, g, metrica, modo)
        ax.set_xlabel("passo"); ax.set_xticks(PASSOS); ax.set_ylabel(descritiva.UNIDADES[metrica]); ax.grid(alpha=0.3)
    eixos[0, 0].legend()
    fig.suptitle("Média por modo (faixa: IC 95% entre cadeias)", fontsize=10)
    _salvar(fig, caminho)


def cabe_tensiona(df: pd.DataFrame, caminho: Path) -> None:
    """H5: regressão e violações novas nos passos cujo pedido cabe × tensiona a arquitetura."""
    d = descritiva.violacoes_novas(df).copy()
    d["taxa"] = 100 * d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    paineis = (("taxa", descritiva.UNIDADES["taxa_regressao"]), ("violacoes_novas", "violações ArchUnit novas no passo"))
    fig, eixos = plt.subplots(1, 2, figsize=(10, 4))
    tipos = ("cabe", "tensiona")
    for ax, (coluna, rotulo) in zip(eixos, paineis):
        for j, modo in enumerate(("incremental", "regenerado")):
            for i, tipo in enumerate(tipos):
                m, h = _media_ic(d[(d["mode"] == modo) & (d["request_type"] == tipo)][coluna])
                x = i + (j - 0.5) * 0.25
                ax.errorbar(x, m, yerr=h, fmt=MARCADORES[tipo], color=CORES[modo], capsize=4,
                            label=modo if i == 0 else None)
        ax.set_xticks(range(len(tipos))); ax.set_xticklabels([f"pedido que {t}" for t in tipos])
        ax.set_ylabel(rotulo); ax.grid(alpha=0.3, axis="y")
    eixos[0].legend()
    fig.suptitle("Média dos passos por tipo de pedido (barra: IC 95%)", fontsize=10)
    _salvar(fig, caminho)


def kaplan_meier(km: pd.DataFrame, caminho: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    for modo, g in km.groupby("mode"):
        ax.step(g["tempo"], g["sobrevivencia"], where="post", label=modo, color=CORES[modo])
        ax.fill_between(g["tempo"], g["ic_inf"], g["ic_sup"], step="post", alpha=0.15, color=CORES[modo])
    ax.set_xlabel("passo"); ax.set_xticks(PASSOS); ax.set_ylabel("P(sem regressão até o passo)")
    ax.set_ylim(0, 1.02); ax.legend(); ax.grid(alpha=0.3)
    _salvar(fig, caminho)


def diferenca_pareada(df: pd.DataFrame, pareada: pd.DataFrame, caminho: Path) -> None:
    """Diferença incremental − regenerado por passo: um ponto por par, mediana com IC e delta de Cliff."""
    d = df[(df["step"] >= 1) & (df["status"] == "ok")].copy()
    d["taxa"] = 100 * d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    larga = d.pivot_table(index=["chain_id", "step"], columns="mode", values="taxa").dropna().reset_index()
    larga["dif"] = larga["incremental"] - larga["regenerado"]
    rng = np.random.default_rng(42)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axhline(0, color="black", lw=0.8)
    ax.scatter(larga["step"] + rng.uniform(-0.15, 0.15, len(larga)), larga["dif"], s=12, color="#555", alpha=0.5, label="par (cadeia i)")
    p = pareada.set_index("passo")
    ax.errorbar(p.index, 100 * p["dif_mediana"],
                yerr=[100 * (p["dif_mediana"] - p["dif_mediana_ic95_inf"]), 100 * (p["dif_mediana_ic95_sup"] - p["dif_mediana"])],
                fmt="D", color="black", capsize=3, label="mediana (IC 95% bootstrap)")
    topo = ax.get_ylim()[1]
    for passo, linha in p.iterrows():
        ax.annotate(f"δ={linha['cliffs_delta']:.2f}", (passo, topo), ha="center", va="bottom", fontsize=7)
    ax.set_xlabel("passo"); ax.set_xticks(range(1, 11))
    ax.set_ylabel("incremental − regenerado\n(pontos percentuais de regressão)")
    ax.legend(loc="lower left", fontsize=8); ax.grid(alpha=0.3)
    _salvar(fig, caminho)


def todas(df: pd.DataFrame, km: pd.DataFrame, pareada: pd.DataFrame, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    regressao_por_cadeia(df, pasta / "regressao_por_cadeia.png")
    regressao_acumulada(df, pasta / "regressao_acumulada.png")
    estrutura_por_passo(df, pasta / "estrutura_por_passo.png")
    cabe_tensiona(df, pasta / "cabe_tensiona.png")
    kaplan_meier(km, pasta / "kaplan_meier.png")
    diferenca_pareada(df, pareada, pasta / "diferenca_pareada.png")
