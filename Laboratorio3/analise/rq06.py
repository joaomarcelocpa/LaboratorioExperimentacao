"""RQ 06: fatores associados ao desempenho DORA."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from analise import comum


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


ROTULOS_FATOR = {"linguagem_top": "linguagem", "estrelas_q": "estrelas", "contribuidores_q": "contribuidores",
                 "idade_q": "idade", "tipo_projeto": "tipo do projeto (n=60)"}
ROTULOS_METRICA = {"freq_release": "frequência", "lt_commit_h": "lead time (b)", "cfr_a": "CFR (a)",
                   "cfr_b": "CFR (b)", "recuperacao_h": "recuperação"}


def plotar_efeitos(tabela: pd.DataFrame) -> None:
    """Mapa de ε² por fator × métrica; o asterisco marca p ajustado (Holm) < 0,05."""
    t = tabela[tabela["teste"] == "kruskal"]
    efeito = t.pivot(index="fator", columns="metrica", values="epsilon2")
    ajust = t.pivot(index="fator", columns="metrica", values="p_ajustado")
    efeito = efeito.reindex(index=list(ROTULOS_FATOR), columns=list(ROTULOS_METRICA))
    ajust = ajust.reindex_like(efeito)
    fig, ax = comum.plt.subplots(figsize=(7.5, 4))
    im = ax.imshow(efeito.values, cmap="Blues", vmin=0, vmax=0.2, aspect="auto")
    for i in range(efeito.shape[0]):
        for j in range(efeito.shape[1]):
            v = efeito.values[i, j]
            marca = "*" if ajust.values[i, j] < 0.05 else ""
            ax.text(j, i, f"{v:.2f}{marca}", ha="center", va="center",
                    color="white" if v > 0.12 else "black", fontsize=10)
    ax.set_xticks(range(efeito.shape[1]), [ROTULOS_METRICA[c] for c in efeito.columns])
    ax.set_yticks(range(efeito.shape[0]), [ROTULOS_FATOR[f] for f in efeito.index])
    ax.set_title("RQ 06 · tamanho de efeito (ε²) de cada fator sobre cada métrica\n* = significativo após Holm")
    fig.colorbar(im, ax=ax, label="ε²")
    comum.salvar_figura(fig, "rq06_efeitos")


def main() -> None:
    metricas = comum.carregar_metricas()
    repos = comum.carregar_repos()
    consenso_path = comum.RAIZ / "data/conferencia/consenso_repositorios.csv"
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
    comum.salvar_tabela(tabela.set_index("fator"), "rq06_fatores")
    plotar_efeitos(tabela)


if __name__ == "__main__":  # pragma: no cover
    main()
