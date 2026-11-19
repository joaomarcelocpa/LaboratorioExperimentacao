"""Complexidade ciclomática máxima e linhas de código (Lizard) de src/main/java."""

from __future__ import annotations

from pathlib import Path

import lizard

from metrics.java import DIR_FONTES


def medir(raiz: Path) -> dict[str, int]:
    arquivos = [str(f) for f in sorted((Path(raiz) / DIR_FONTES).rglob("*.java"))]
    max_ccn, loc = 0, 0
    for info in lizard.analyze_files(arquivos):
        loc += info.nloc
        for fn in info.function_list:
            max_ccn = max(max_ccn, fn.cyclomatic_complexity)
    return {"max_ccn": max_ccn, "loc": loc}


def versao() -> str:
    return lizard.version
