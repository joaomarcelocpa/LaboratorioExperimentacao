"""Mede um workspace e devolve as colunas de produto do CSV por passo.

    python -m metrics.coletar <workspace> [--commit HEAD] [--pacote-base com.x]

Saída (JSON no stdout, ou CSV com --csv): arch_violations, cycles,
files_touched, modules_touched, max_ccn, dup_pct, loc, doc_drift, mais o
detalhe e as fontes usadas (ArchUnit ou estática, jdeps ou fontes).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics import arquitetura, complexidade, deriva, duplicacao, grafo, localidade
from metrics.java import carregar_projeto

COLUNAS = ("arch_violations", "cycles", "files_touched", "modules_touched", "max_ccn", "dup_pct", "loc", "doc_drift")


def coletar(raiz: Path, commit: str = "HEAD", pacote_base: str | None = None, com_jscpd: bool = True,
            com_archunit: bool = True, com_jdeps: bool = True) -> dict:
    raiz = Path(raiz)
    p = carregar_projeto(raiz, pacote_base)
    g, fonte_grafo = grafo.dependencias(p, com_jdeps)
    arq = arquitetura.medir(p, com_archunit, com_jdeps)
    cx = complexidade.medir(raiz)
    loc = localidade.medir(raiz, p.pacote_base, commit)
    drift = deriva.medir(p, arq)
    return {
        "arch_violations": arq.violacoes,
        "cycles": grafo.ciclos(g),
        "files_touched": loc["files_touched"],
        "modules_touched": loc["modules_touched"],
        "max_ccn": cx["max_ccn"],
        "dup_pct": duplicacao.medir(raiz) if com_jscpd else None,
        "loc": cx["loc"],
        "doc_drift": drift["doc_drift"],
        "detalhe": {
            "pacote_base": p.pacote_base,
            "violacoes_por_regra": arq.por_regra,
            "violacoes": arq.detalhes,
            "fonte_arch_violations": arq.fonte,
            "fonte_grafo": fonte_grafo,
            "modulos_nao_documentados": drift["modulos_nao_documentados"],
            "documento_arquitetura": drift["documento"],
        },
    }


def principal(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Métricas estruturais de um workspace Java.")
    ap.add_argument("workspace", type=Path)
    ap.add_argument("--commit", default="HEAD", help="commit do passo (para a localidade da mudança)")
    ap.add_argument("--pacote-base", default=None)
    ap.add_argument("--sem-jscpd", action="store_true")
    ap.add_argument("--sem-archunit", action="store_true", help="não roda mvn; usa só a verificação estática")
    ap.add_argument("--sem-jdeps", action="store_true", help="grafo pelos imports, sem jdeps")
    ap.add_argument("--csv", action="store_true", help="imprime só as 8 colunas, em CSV")
    args = ap.parse_args(argv)
    r = coletar(args.workspace, args.commit, args.pacote_base, not args.sem_jscpd, not args.sem_archunit, not args.sem_jdeps)
    if args.csv:
        print(",".join(COLUNAS))
        print(",".join("" if r[c] is None else str(r[c]) for c in COLUNAS))
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    principal()
