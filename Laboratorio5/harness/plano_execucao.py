"""Plano de execucao da coleta: tabela cadeia x modo x ordem x maquina, sorteada com semente fixa.

Uso:
    python -m harness.plano_execucao --cadeias-por-modo 12 --semente 118 --saida docs/s02/plano-de-execucao.csv

Balanceamento: dentro de cada modo, cada combinacao (ordem, maquina) recebe o mesmo numero de cadeias, o que
exige cadeias-por-modo multiplo de (2 ordens x maquinas). O sorteio nao usa o modulo random, cujo embaralhamento
pode mudar entre versoes do Python: ordena por SHA-256 de "semente:chave", reproduzivel em qualquer maquina.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

MODOS = ("incremental", "regenerado")
ORDENS = ("A", "B")
MAQUINAS = ("A", "B", "C")
COLUNAS = ("cadeia_id", "modo", "ordem", "maquina", "posicao_na_maquina")


def _chave(semente: int, texto: str) -> str:
    return hashlib.sha256(f"{semente}:{texto}".encode()).hexdigest()


def _sortear(itens: list, semente: int, rotulo: str) -> list:
    return sorted(itens, key=lambda i: _chave(semente, f"{rotulo}:{i}"))


def gerar(cadeias_por_modo: int, semente: int, maquinas: tuple[str, ...] = MAQUINAS) -> list[dict]:
    celulas = len(ORDENS) * len(maquinas)
    if cadeias_por_modo % celulas:
        raise ValueError(
            f"cadeias por modo ({cadeias_por_modo}) deve ser multiplo de {celulas} "
            f"({len(ORDENS)} ordens x {len(maquinas)} maquinas) para o plano ficar balanceado")
    repeticoes = cadeias_por_modo // celulas
    plano: list[dict] = []
    for modo in MODOS:
        combinacoes = [(o, m) for o in ORDENS for m in maquinas for _ in range(repeticoes)]
        # o indice na lista desambigua repeticoes; o sorteio decide qual cadeia cai em qual celula
        indexadas = [(i, o, m) for i, (o, m) in enumerate(combinacoes)]
        sorteadas = _sortear(indexadas, semente, f"celula:{modo}")
        for n, (_, ordem, maquina) in enumerate(sorteadas, start=1):
            plano.append({"cadeia_id": f"{modo[:3]}-{n:02d}", "modo": modo, "ordem": ordem,
                          "maquina": maquina, "posicao_na_maquina": 0})
    # ordem de execucao em cada maquina: modos e ordens misturados, para a deriva do ambiente nao
    # coincidir com um modo
    for maquina in maquinas:
        dela = [c for c in plano if c["maquina"] == maquina]
        fila = sorted(dela, key=lambda c: _chave(semente, f"fila:{maquina}:{c['cadeia_id']}"))
        for pos, c in enumerate(fila, start=1):
            c["posicao_na_maquina"] = pos
    return sorted(plano, key=lambda c: (c["maquina"], c["posicao_na_maquina"]))


def escrever(plano: list[dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, lineterminator="\n")
        w.writeheader()
        w.writerows(plano)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cadeias-por-modo", type=int, required=True)
    p.add_argument("--semente", type=int, default=118)
    p.add_argument("--saida", type=Path, default=Path("docs/s02/plano-de-execucao.csv"))
    a = p.parse_args(argv)
    plano = gerar(a.cadeias_por_modo, a.semente)
    escrever(plano, a.saida)
    print(f"{len(plano)} cadeias em {a.saida} (semente {a.semente})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
