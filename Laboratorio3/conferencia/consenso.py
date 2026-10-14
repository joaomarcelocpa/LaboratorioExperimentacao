"""Consenso por maioria dos rótulos da conferência manual.

Uso: python -m conferencia.consenso [--pasta data/conferencia]

Regra (docs/protocolo_desempate.md): vale a resposta que mais da metade dos
avaliadores deu. Sem maioria (1-1-1), o item vira empate, fica sem consenso e é
decidido em reunião; a decisão vai em desempates.csv e é aplicada na próxima
execução.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

from conferencia.rotulos import (
    TABELAS, ErroDeRotulo, carregar, colunas_da_dimensao, normalizar,
)

COLUNAS_DESEMPATE = ["dimensao", "repo", "tag", "valor"]


def maioria(respostas: list[str]) -> tuple[str | None, str]:
    """(consenso, situacao): 'unanime', 'maioria' ou 'empate' (consenso None)."""
    contagem = Counter(respostas).most_common()
    valor, votos = contagem[0]
    if votos == len(respostas):
        return valor, "unanime"
    if votos > len(respostas) / 2:
        return valor, "maioria"
    return None, "empate"


def _ler_desempates(caminho: Path) -> dict[tuple[str, str, str], str]:
    if not caminho.exists():
        return {}
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if list(df.columns) != COLUNAS_DESEMPATE:
        raise ErroDeRotulo(f"{caminho.name} deve ter as colunas {COLUNAS_DESEMPATE}")
    return {
        (r.dimensao, r.repo, r.tag): normalizar(r.valor) for r in df.itertuples()
    }


def calcular(
    tabelas: dict[str, pd.DataFrame],
    desempates: dict[tuple[str, str, str], str] | None = None,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Retorna ({tabela: consenso final}, divergências em formato longo)."""
    desempates = desempates or {}
    consensos: dict[str, pd.DataFrame] = {}
    divergencias: list[dict] = []
    for tabela, (chave, dimensoes) in TABELAS.items():
        df = tabelas[tabela]
        final = pd.DataFrame(index=df.index)
        for dim in dimensoes:
            cols = colunas_da_dimensao(df, dim)
            valores = []
            for idx, linha in df[cols].iterrows():
                idx_t = idx if isinstance(idx, tuple) else (idx,)
                valor, situacao = maioria(list(linha.values))
                if situacao == "empate":
                    chave_d = (dim, idx_t[0], idx_t[1] if len(idx_t) > 1 else "")
                    if chave_d in desempates:
                        valor, situacao = desempates[chave_d], "desempate"
                if situacao != "unanime":
                    divergencias.append({
                        "tabela": tabela, "dimensao": dim,
                        "repo": idx_t[0], "tag": idx_t[1] if len(idx_t) > 1 else "",
                        **{c.split("__", 1)[1]: v for c, v in linha.items()},
                        "consenso": valor or "", "situacao": situacao,
                    })
                valores.append(valor)
            final[dim] = valores
        consensos[tabela] = final
    colunas = ["tabela", "dimensao", "repo", "tag"]
    div = pd.DataFrame(divergencias)
    if div.empty:
        div = pd.DataFrame(columns=colunas + ["consenso", "situacao"])
    else:
        avaliadores = [c for c in div.columns if c not in colunas + ["consenso", "situacao"]]
        div = div[colunas + avaliadores + ["consenso", "situacao"]]
    return consensos, div


def gerar(pasta: Path) -> dict[str, int]:
    pasta = Path(pasta)
    tabelas = carregar(pasta)
    consensos, div = calcular(tabelas, _ler_desempates(pasta / "desempates.csv"))
    for tabela, df in consensos.items():
        df.reset_index().to_csv(pasta / f"consenso_{tabela}.csv", index=False)
    div.to_csv(pasta / "divergencias.csv", index=False)
    empates = div[div["situacao"] == "empate"]
    empates.to_csv(pasta / "empates_para_reuniao.csv", index=False)
    return {
        "itens_divergentes": len(div),
        "empates_abertos": len(empates),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conferencia.consenso")
    parser.add_argument("--pasta", default="data/conferencia")
    args = parser.parse_args(argv)
    try:
        r = gerar(Path(args.pasta))
    except ErroDeRotulo as e:
        print(f"erro nos rótulos:\n{e}", file=sys.stderr)
        return 1
    print(f"respostas divergentes: {r['itens_divergentes']}")
    print(f"empates sem decisão (levar à reunião): {r['empates_abertos']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
