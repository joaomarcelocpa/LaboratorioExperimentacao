"""Estatística descritiva por modo, passo e tipo de pedido (issue #123).

Toda tabela mostra o tamanho da amostra do passo e quantas cadeias já foram
censuradas por passo falho, para que a queda de n ao longo da cadeia fique
visível. Nenhum índice composto: cada métrica aparece na sua própria unidade.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Métricas por passo, com a unidade usada em tabelas e eixos de gráficos.
UNIDADES: dict[str, str] = {
    "taxa_regressao": "% da suíte de regressão falhando",
    "arch_violations": "violações ArchUnit (contagem)",
    "cycles": "ciclos entre pacotes (contagem)",
    "files_touched": "arquivos no diff do passo",
    "modules_touched": "módulos no diff do passo",
    "doc_drift": "deriva documento × código (contagem)",
    "max_ccn": "maior complexidade ciclomática",
    "dup_pct": "% de linhas duplicadas",
    "loc": "linhas de código (src/main)",
    "tokens_in": "tokens de entrada",
    "tokens_out": "tokens de saída",
    "cost_usd": "custo (USD)",
    "duration_s": "duração (s)",
    "turns": "turnos do agente",
}
METRICAS = tuple(UNIDADES)


def _com_taxa(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["taxa_regressao"] = 100 * d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    return d


def _censura(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada (modo, passo): cadeias iniciadas, ok e censuradas até o passo (inclusive)."""
    fim = df[df["status"] == "falha"].groupby(["chain_id", "mode"])["step"].min().rename("passo_falho").reset_index()
    linhas = []
    for (modo, passo), g in df.groupby(["mode", "step"]):
        linhas.append({
            "mode": modo, "step": int(passo),
            "cadeias_no_passo": int(g["chain_id"].nunique()),
            "cadeias_ok": int((g["status"] == "ok").sum()),
            "censuradas_ate_o_passo": int(((fim["mode"] == modo) & (fim["passo_falho"] <= passo)).sum()),
        })
    return pd.DataFrame(linhas)


def regressao_acumulada(df: pd.DataFrame) -> pd.DataFrame:
    """Por (modo, passo): fração das cadeias observadas no passo que já regrediram em algum passo até ele."""
    d = df[df["status"] == "ok"].sort_values(["chain_id", "mode", "step"]).copy()
    d["ja_regrediu"] = d.groupby(["chain_id", "mode"])["reg_failed"].transform(lambda s: (s.astype(float) > 0).cummax())
    return (
        d.groupby(["mode", "step"])
        .agg(cadeias_com_regressao_no_passo=("reg_failed", lambda s: float((s.astype(float) > 0).mean())),
             regressao_acumulada=("ja_regrediu", "mean"))
        .reset_index()
    )


def por_passo(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela larga: uma linha por (modo, passo), com n, censura e a média de cada métrica."""
    d = _com_taxa(df[df["status"] == "ok"])
    medias = d.groupby(["mode", "step"])[list(METRICAS)].mean().reset_index()
    return _censura(df).merge(regressao_acumulada(df), on=["mode", "step"], how="left").merge(medias, on=["mode", "step"], how="left")


def por_passo_completa(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela longa: (modo, passo, métrica) com n, média, desvio, mediana, mínimo e máximo."""
    d = _com_taxa(df[df["status"] == "ok"])
    longa = d.melt(id_vars=["mode", "step"], value_vars=list(METRICAS), var_name="metrica", value_name="valor").dropna()
    longa["valor"] = longa["valor"].astype(float)
    t = (
        longa.groupby(["mode", "step", "metrica"])["valor"]
        .agg(n="count", media="mean", dp="std", mediana="median", minimo="min", maximo="max")
        .reset_index()
    )
    t["unidade"] = t["metrica"].map(UNIDADES)
    ordem = {m: i for i, m in enumerate(METRICAS)}
    return t.sort_values(["metrica", "mode", "step"], key=lambda s: s.map(ordem) if s.name == "metrica" else s).reset_index(drop=True)


def violacoes_novas(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas dos passos >= 1 com `violacoes_novas` = arch_violations − passo anterior da mesma cadeia."""
    d = df[df["status"] == "ok"].sort_values(["chain_id", "mode", "step"]).copy()
    d["violacoes_novas"] = d.groupby(["chain_id", "mode"])["arch_violations"].diff().astype(float)
    return d[(d["step"] >= 1) & d["violacoes_novas"].notna()]


def por_tipo_de_pedido(df: pd.DataFrame) -> pd.DataFrame:
    """H5: comparação cabe × tensiona por modo (passos >= 1 concluídos)."""
    d = _com_taxa(violacoes_novas(df))
    d["acc_falha_pct"] = 100 * d["acc_failed"].astype(float) / d["acc_total"].astype(float).replace(0, np.nan)
    d["regrediu"] = (d["reg_failed"].astype(float) > 0).astype(float)
    return (
        d.groupby(["mode", "request_type"])
        .agg(passos=("step", "count"), cadeias=("chain_id", "nunique"),
             taxa_regressao=("taxa_regressao", "mean"), passos_com_regressao=("regrediu", "mean"),
             violacoes_novas=("violacoes_novas", "mean"), files_touched=("files_touched", "mean"),
             modules_touched=("modules_touched", "mean"), dup_pct=("dup_pct", "mean"),
             aceitacao_falha_pct=("acc_falha_pct", "mean"))
        .reset_index()
    )


def resumo_da_coleta(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por modo: cadeias, passos, falhas, novas tentativas, censura e custo."""
    linhas = []
    for modo, g in df.groupby("mode"):
        exec_ = g[g["step"] >= 1]
        falhas = g[g["status"] == "falha"]
        linhas.append({
            "mode": modo,
            "cadeias": int(g["chain_id"].nunique()),
            "passos_executados": len(exec_),
            "passos_ok": int((exec_["status"] == "ok").sum()),
            "passos_com_nova_tentativa": int(exec_["retry"].astype(float).sum()),
            "cadeias_censuradas_por_falha": int(falhas["chain_id"].nunique()),
            "cadeias_completas": int(g[g["step"] == g["step"].max()]["status"].eq("ok").sum()),
            "custo_total_usd": float(exec_["cost_usd"].astype(float).sum()),
            "tokens_totais": float(exec_["tokens_in"].astype(float).sum() + exec_["tokens_out"].astype(float).sum()),
            "duracao_total_h": float(exec_["duration_s"].astype(float).sum() / 3600),
            "agente_rodou_testes_pct": float(100 * exec_["agent_ran_tests"].astype(float).mean()),
        })
    return pd.DataFrame(linhas)


def tabelas(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "resumo_da_coleta": resumo_da_coleta(df),
        "por_passo": por_passo(df),
        "por_passo_completa": por_passo_completa(df),
        "por_tipo_de_pedido": por_tipo_de_pedido(df),
    }
