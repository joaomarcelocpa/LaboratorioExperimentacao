"""Roda todas as análises da S03 a partir dos CSVs, sem coletar nada.

Uso: python -m analise   (ou `make reproduce`)

Cada módulo `analise/rq*.py` expõe uma função `main()`. Os módulos são
executados em ordem alfabética, então `rq01_rq02` roda antes de `rq07`.
"""
from __future__ import annotations

import importlib
import pkgutil
import sys

import analise


def descobrir() -> list[str]:
    return sorted(m.name for m in pkgutil.iter_modules(analise.__path__) if m.name.startswith("rq"))


def main() -> int:
    modulos = descobrir()
    if not modulos:
        print("Nenhuma análise encontrada em analise/rq*.py")
        return 0
    for nome in modulos:
        print(f"== {nome}")
        importlib.import_module(f"analise.{nome}").main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
