"""Kappa de Fleiss da concordância entre os avaliadores, por dimensão.

Uso: python -m conferencia.kappa [--pasta data/conferencia]
Escreve kappa.csv com uma linha por pergunta (tipo_projeto, entregas_reais,
corretiva).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from conferencia.rotulos import (
    TABELAS, VOCABULARIO, ErroDeRotulo, carregar, colunas_da_dimensao,
)


def interpretar(kappa: float) -> str:
    """Faixas de Landis e Koch (1977)."""
    if math.isnan(kappa):
        return "indefinido (todos usaram uma única categoria)"
    if kappa < 0:
        return "pior que o acaso"
    for limite, nome in [(0.20, "leve"), (0.40, "razoável"), (0.60, "moderada"),
                         (0.80, "substancial")]:
        if kappa <= limite:
            return nome
    return "quase perfeita"


def kappa_da_dimensao(respostas: pd.DataFrame, dimensao: str) -> dict:
    """respostas: uma linha por item, uma coluna por avaliador."""
    categorias = VOCABULARIO[dimensao]
    codigos = respostas.apply(lambda col: col.map(categorias.index)).to_numpy()
    tabela, _ = aggregate_raters(codigos, n_cat=len(categorias))
    usadas = (tabela.sum(axis=0) > 0).sum()
    valor = float(fleiss_kappa(tabela, method="fleiss")) if usadas > 1 else float("nan")
    return {
        "dimensao": dimensao,
        "n_itens": len(respostas),
        "n_avaliadores": respostas.shape[1],
        "kappa": valor,
        "interpretacao": interpretar(valor),
        "pct_unanime": float((respostas.nunique(axis=1) == 1).mean()),
    }


def calcular(tabelas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    linhas = []
    for tabela, (_, dimensoes) in TABELAS.items():
        df = tabelas[tabela]
        for dim in dimensoes:
            resp = df[colunas_da_dimensao(df, dim)]
            linhas.append(kappa_da_dimensao(resp, dim))
    return pd.DataFrame(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conferencia.kappa")
    parser.add_argument("--pasta", default="data/conferencia")
    args = parser.parse_args(argv)
    pasta = Path(args.pasta)
    try:
        resultado = calcular(carregar(pasta))
    except ErroDeRotulo as e:
        print(f"erro nos rótulos:\n{e}", file=sys.stderr)
        return 1
    resultado.to_csv(pasta / "kappa.csv", index=False)
    for r in resultado.itertuples():
        print(f"{r.dimensao}: kappa {r.kappa:.3f} ({r.interpretacao}); "
              f"{r.pct_unanime:.0%} dos itens com resposta igual dos {r.n_avaliadores}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
