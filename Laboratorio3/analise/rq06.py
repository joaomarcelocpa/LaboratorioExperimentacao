"""RQ 06: fatores associados ao desempenho DORA."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests


def quartis_labels(serie: pd.Series) -> pd.Series:
    """Divide série numérica em 4 quartis rotulados Q1..Q4 (Q1 = menor).

    duplicates='drop' evita erro quando muitos valores são idênticos.
    """
    return pd.qcut(serie, q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")


def mapear_linguagem(serie: pd.Series, top_n: int = 7) -> pd.Series:
    """Mantém as top_n linguagens mais frequentes; as demais viram 'Outras'."""
    top = serie.value_counts().head(top_n).index
    return serie.where(serie.isin(top), other="Outras")


def testar_kruskal(grupos: dict[str, pd.Series]) -> dict:
    """Kruskal-Wallis para múltiplos grupos; retorna H, pvalue, ε², n_total, n_por_grupo."""
    amostras = [v.dropna().values for v in grupos.values()]
    H, p = stats.kruskal(*amostras)
    n_total = sum(len(a) for a in amostras)
    epsilon2 = H / (n_total - 1) if n_total > 1 else float("nan")
    return {
        "teste": "kruskal",
        "H": float(H),
        "pvalue": float(p),
        "epsilon2": float(epsilon2),
        "n_total": n_total,
        "n_por_grupo": {k: len(v.dropna()) for k, v in grupos.items()},
    }


def testar_mann_whitney(x: pd.Series, y: pd.Series) -> dict:
    """Mann-Whitney U e Cliff's delta entre dois grupos."""
    a, b = x.dropna().values, y.dropna().values
    n1, n2 = len(a), len(b)
    result = stats.mannwhitneyu(a, b, alternative="two-sided")
    U1 = float(result.statistic)
    cliff_delta = 2 * U1 / (n1 * n2) - 1 if n1 * n2 > 0 else float("nan")
    return {
        "teste": "mann_whitney",
        "U": U1,
        "pvalue": float(result.pvalue),
        "cliff_delta": float(cliff_delta),
        "n1": n1,
        "n2": n2,
        "n_total": n1 + n2,
    }


def testar_fator_metrica(df: pd.DataFrame, fator_col: str, metrica_col: str) -> dict:
    """Testa associação fator × métrica; escolhe Kruskal ou Mann-Whitney pelo nº de grupos.

    Descarta NaN tanto no fator quanto na métrica antes de agrupar.
    """
    sub = df[[fator_col, metrica_col]].dropna(subset=[fator_col, metrica_col])
    grupos = {
        str(g): sub.loc[sub[fator_col] == g, metrica_col]
        for g in sub[fator_col].unique()
    }
    grupos = {k: v for k, v in grupos.items() if len(v) >= 2}
    n_grupos = len(grupos)
    resultado = {"fator": fator_col, "metrica": metrica_col}
    if n_grupos < 2:
        resultado.update({"teste": "skip", "pvalue": float("nan"), "n_total": 0})
    elif n_grupos == 2:
        k1, k2 = list(grupos.keys())
        resultado.update(testar_mann_whitney(grupos[k1], grupos[k2]))
    else:
        resultado.update(testar_kruskal(grupos))
    return resultado


def corrigir_holm(resultados: list[dict]) -> pd.DataFrame:
    """Aplica correção de Holm nos p-valores válidos; skip fica como NaN."""
    df = pd.DataFrame(resultados)
    is_skip = df.get("teste", pd.Series(["ok"] * len(df))) == "skip"
    validos = df["pvalue"].notna() & ~is_skip
    pvals = df.loc[validos, "pvalue"].values
    if len(pvals) > 0:
        _, p_adj, _, _ = multipletests(pvals, method="holm")
        df.loc[validos, "p_ajustado"] = p_adj
    df.loc[~validos, "p_ajustado"] = float("nan")
    return df


def montar_fatores(
    metricas: pd.DataFrame,
    repos: pd.DataFrame,
    consenso: pd.DataFrame | None,
) -> pd.DataFrame:
    """Junta métricas, fatores de repos e tipo_projeto do consenso num DataFrame."""
    df = metricas.merge(
        repos[["repo", "linguagem", "estrelas", "contribuidores", "idade_anos"]],
        on="repo",
    )
    df["linguagem_top"] = mapear_linguagem(df["linguagem"], top_n=7)
    df["estrelas_q"] = quartis_labels(df["estrelas"])
    df["contribuidores_q"] = quartis_labels(df["contribuidores"])
    df["idade_q"] = quartis_labels(df["idade_anos"])
    if consenso is not None and not consenso.empty:
        df = df.merge(consenso[["repo", "tipo_projeto"]], on="repo", how="left")
    return df


if __name__ == "__main__":  # pragma: no cover
    raiz = Path(__file__).parent.parent
    metricas = pd.read_csv(raiz / "data/processed/metricas.csv")
    repos = pd.read_csv(raiz / "data/processed/repos.csv")
    consenso_path = raiz / "data/conferencia/consenso_repositorios.csv"
    consenso = pd.read_csv(consenso_path) if consenso_path.exists() else None

    df = montar_fatores(metricas, repos, consenso)

    FATORES = ["linguagem_top", "estrelas_q", "contribuidores_q", "idade_q"]
    if "tipo_projeto" in df.columns:
        FATORES.append("tipo_projeto")

    METRICAS = [
        ("freq_release", "RQ01"),
        ("lt_commit_h", "RQ02b"),
        ("cfr_a", "RQ03a"),
        ("cfr_b", "RQ03b"),
        ("recuperacao_h", "RQ04"),
    ]

    resultados = []
    for fator in FATORES:
        for metrica_col, rq in METRICAS:
            r = testar_fator_metrica(df, fator, metrica_col)
            r["rq"] = rq
            n_grupos = r.get("n_por_grupo", {})
            r["grupos_n"] = "; ".join(f"{k}={v}" for k, v in n_grupos.items()) if n_grupos else ""
            resultados.append(r)

    tabela = corrigir_holm(resultados)

    cols_exibir = ["fator", "metrica", "rq", "teste", "pvalue", "p_ajustado", "n_total"]
    for col_ef in ("epsilon2", "cliff_delta"):
        if col_ef in tabela.columns:
            cols_exibir.append(col_ef)
    cols_exibir.append("grupos_n")

    print("\n=== RQ 06 · Fatores × Métricas DORA (com correção de Holm) ===")
    print(tabela[[c for c in cols_exibir if c in tabela.columns]].to_string(index=False))
