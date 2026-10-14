"""Valida as variantes da heurística de release corretiva contra os rótulos manuais.

Uso:
    python -m metricas.validacao_heuristica \
        --labels data/conferencia/planilha_releases_B.csv \
        [--threshold 0.20]

Saída (stdout): tabela com precision, recall e F1 para v1-v4.
Também imprime CFR(b) segmentado por repositórios SemVer vs não-SemVer.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Literal

import pandas as pd

# Importa a heurística com suporte a variantes
from metricas.corretiva import eh_corretiva, parse_semver, VarianteHeuristica

try:
    from sklearn.metrics import precision_recall_fscore_support
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


_COMMIT_PREFIXO_RE = re.compile(r"^[-*•]\s*")


def _extrair_commits(texto: str) -> list[str]:
    """Extrai mensagens de commit do campo 'commits' da planilha."""
    if not texto or texto == "nan":
        return []
    linhas = [_COMMIT_PREFIXO_RE.sub("", l.strip()) for l in texto.splitlines()]
    return [l for l in linhas if l]


def _prev_tag_por_repo(df: pd.DataFrame) -> dict[tuple[str, str], str | None]:
    """Para cada (repo, tag), retorna a tag imediatamente anterior (por data)."""
    resultado: dict[tuple[str, str], str | None] = {}
    for repo, grupo in df.groupby("repo"):
        grupo_sorted = grupo.sort_values("publicada_em").reset_index(drop=True)
        for i, row in grupo_sorted.iterrows():
            chave = (repo, row["tag"])
            resultado[chave] = grupo_sorted.iloc[i - 1]["tag"] if i > 0 else None
    return resultado


_NOTAS_CORRETIVO_RE = re.compile(
    r"\b(fix|bug|hotfix|revert|regression|patch|security|vulnerability|cve|crash)\b",
    re.IGNORECASE,
)
_HOTFIX_REVERT_RE = re.compile(r"\b(hotfix|revert)\b", re.IGNORECASE)


def _aplicar_variante(
    df: pd.DataFrame,
    prev: dict[tuple[str, str], str | None],
    variante: VarianteHeuristica,
    pct_threshold: float = 0.20,
) -> list[bool]:
    predicoes: list[bool] = []
    for _, row in df.iterrows():
        repo = row["repo"]
        tag = row["tag"]
        tag_ant = prev.get((repo, tag))
        commits_texto = str(row.get("commits", ""))
        mensagens = _extrair_commits(commits_texto)
        commits_df = pd.DataFrame([{"mensagem": m, "eh_bot": False} for m in mensagens])
        notas = str(row.get("notas", "")) if variante in ("v4", "v5") else ""

        if tag_ant is None:
            # Primeira release do repo no dataset — pipeline não aplica a
            # heurística aqui, mas para fins de validação usamos sinais das notas.
            notas_fix = bool(_NOTAS_CORRETIVO_RE.search(str(row.get("notas", ""))))
            has_hotfix = (not commits_df.empty and commits_df["mensagem"].apply(
                lambda m: bool(_HOTFIX_REVERT_RE.search(str(m)))
            ).any())
            pct_fix_fr = (float(commits_df["mensagem"].apply(
                lambda m: bool(re.search(r"\bfix\b", str(m), re.IGNORECASE))
            ).mean()) if not commits_df.empty else 0.0)
            pred = notas_fix or has_hotfix or pct_fix_fr >= 0.50
            predicoes.append(pred)
            continue

        pred = eh_corretiva(
            tag_ant, tag, commits_df,
            variante=variante,
            notas=notas,
            pct_threshold=pct_threshold,
        )
        predicoes.append(pred)
    return predicoes


def _f1_manual(verdadeiros: list[bool], predicoes: list[bool]) -> dict:
    """Calcula precision, recall, F1 sem sklearn como fallback."""
    tp = sum(v and p for v, p in zip(verdadeiros, predicoes))
    fp = sum(not v and p for v, p in zip(verdadeiros, predicoes))
    fn = sum(v and not p for v, p in zip(verdadeiros, predicoes))
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"precision": prec, "recall": rec, "f1": f1}


def calcular_metricas_variante(
    verdadeiros: list[bool],
    predicoes: list[bool],
) -> dict[str, float]:
    if _SKLEARN:
        p, r, f, _ = precision_recall_fscore_support(
            verdadeiros, predicoes, average="binary", zero_division=0
        )
        return {"precision": float(p), "recall": float(r), "f1": float(f)}
    return _f1_manual(verdadeiros, predicoes)


def _cfr_b_segmentado(
    df: pd.DataFrame,
    prev: dict[tuple[str, str], str | None],
    pct_threshold: float,
) -> tuple[float, float]:
    """Retorna (cfr_semver, cfr_nao_semver) para a variante v1."""
    preds = _aplicar_variante(df, prev, "v1", pct_threshold)
    df = df.copy()
    df["pred_v1"] = preds

    def _eh_semver(tag: str) -> bool:
        return parse_semver(tag) is not None

    linhas_semver = df[df["tag"].apply(_eh_semver)]
    linhas_nsv = df[~df["tag"].apply(_eh_semver)]

    cfr_sv = linhas_semver["pred_v1"].mean() if not linhas_semver.empty else float("nan")
    cfr_nsv = linhas_nsv["pred_v1"].mean() if not linhas_nsv.empty else float("nan")
    return float(cfr_sv), float(cfr_nsv)


def validar(
    caminho_labels: str | Path,
    pct_threshold: float = 0.20,
    verbose: bool = True,
) -> pd.DataFrame:
    """Executa a validação e devolve DataFrame com a tabela de resultados.

    Imprime a tabela no stdout se verbose=True.
    """
    df = pd.read_csv(caminho_labels)

    # Se não tem publicada_em, tenta merge automático com planilha_releases.csv
    if "publicada_em" not in df.columns:
        planilha_path = Path(caminho_labels).parent / "planilha_releases.csv"
        if planilha_path.exists():
            planilha = pd.read_csv(planilha_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            cols_planilha = [c for c in planilha.columns if c not in ("corretiva",)]
            df = planilha[cols_planilha].merge(df[["repo", "tag", "corretiva"]], on=["repo", "tag"])

    rotulos_validos = df["corretiva"].notna() & (df["corretiva"] != "")
    if not rotulos_validos.all():
        if verbose:
            n_nan = (~rotulos_validos).sum()
            print(
                f"Aviso: {n_nan} linhas sem rótulo (corretiva=NaN) ignoradas.",
                file=sys.stderr,
            )
        df = df[rotulos_validos].copy()

    _MAPA_BOOL = {"sim": True, "nao": False, "true": True, "false": False, "1": True, "0": False}

    def _para_bool(serie: pd.Series) -> list[bool]:
        return [_MAPA_BOOL.get(str(v).lower().strip(), bool(v)) for v in serie]

    verdadeiros = _para_bool(df["corretiva"])
    prev = _prev_tag_por_repo(df)

    # Subconjunto decidível: exclui primeiras releases de cada repo no dataset,
    # pois o pipeline nunca aplica a heurística sem uma release anterior.
    tem_prev = pd.Series([prev.get((r, t)) is not None
                          for r, t in zip(df["repo"], df["tag"])])
    df_dec = df[tem_prev].copy()
    verdadeiros_dec = _para_bool(df_dec["corretiva"])

    linhas = []
    for v in ("v1", "v2", "v3", "v4", "v5"):
        preds_all = _aplicar_variante(df, prev, v, pct_threshold)  # type: ignore[arg-type]
        preds_dec = [p for p, ok in zip(preds_all, tem_prev) if ok]
        m_all = calcular_metricas_variante(verdadeiros, preds_all)
        m_dec = calcular_metricas_variante(verdadeiros_dec, preds_dec)
        linhas.append({
            "variante": v,
            "F1 (todos)": round(m_all["f1"], 3),
            "P (todos)": round(m_all["precision"], 3),
            "R (todos)": round(m_all["recall"], 3),
            "F1 (decidíveis)": round(m_dec["f1"], 3),
            "P (decidíveis)": round(m_dec["precision"], 3),
            "R (decidíveis)": round(m_dec["recall"], 3),
        })

    tabela = pd.DataFrame(linhas)

    cfr_sv, cfr_nsv = _cfr_b_segmentado(df, prev, pct_threshold)

    if verbose:
        print("\n=== Validação da heurística de release corretiva ===")
        print(f"Rótulos avaliados: {len(df)}  |  Decidíveis: {len(df_dec)}")
        print(f"  True (corretiva):  {sum(verdadeiros)} ({sum(verdadeiros)/len(verdadeiros):.1%})")
        print(f"  False:             {len(verdadeiros)-sum(verdadeiros)}")
        print()
        print(tabela.to_string(index=False))
        print()
        n_semver = df["tag"].apply(lambda t: parse_semver(t) is not None).sum()
        n_nao = len(df) - n_semver
        print(f"CFR(b) v1 por tipo de versão (amostra de validação):")
        print(f"  SemVer ({n_semver} releases): {cfr_sv:.1%}")
        print(f"  Não-SemVer ({n_nao} releases): {cfr_nsv:.1%}")
        print()
        print("Nota: 'todos' inclui primeiras releases de cada repo (pipeline nunca")
        print("      as avalia). 'decidíveis' é a comparação justa com o pipeline.")

    return tabela


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Valida heurística de release corretiva.")
    parser.add_argument(
        "--labels",
        default="data/conferencia/planilha_releases_B.csv",
        help="CSV com rótulos manuais (deve ter coluna 'corretiva').",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Threshold de proporção de commits para v3 (padrão: 0.20).",
    )
    args = parser.parse_args()
    validar(args.labels, pct_threshold=args.threshold)
