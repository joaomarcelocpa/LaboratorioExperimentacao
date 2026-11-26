"""CSV por passo: uma linha por (cadeia, modo, passo), so acrescentando, com o esquema congelado de analysis/schema.py."""
from __future__ import annotations

import csv
from pathlib import Path

from analysis.schema import NOMES


class LinhaDuplicada(Exception):
    pass


def _formatar(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, float):
        return f"{valor:.6f}".rstrip("0").rstrip(".") if valor != int(valor) else str(int(valor))
    return str(valor)


def linhas(caminho: Path) -> list[dict[str, str]]:
    if not caminho.exists():
        return []
    with caminho.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def da_cadeia(caminho: Path, chain_id: int, modo: str) -> list[dict[str, str]]:
    return sorted((l for l in linhas(caminho) if l["chain_id"] == str(chain_id) and l["mode"] == modo),
                  key=lambda l: int(l["step"]))


def anexar(caminho: Path, linha: dict) -> None:
    """Acrescenta uma linha. Recusa a chave (chain_id, mode, step) ja gravada: dado bruto nunca e sobrescrito."""
    extras = set(linha) - set(NOMES)
    if extras:
        raise ValueError(f"colunas fora do esquema: {sorted(extras)}")
    chave = (str(linha["chain_id"]), linha["mode"], str(linha["step"]))
    for existente in linhas(caminho):
        if (existente["chain_id"], existente["mode"], existente["step"]) == chave:
            raise LinhaDuplicada(f"ja existe linha para {chave} em {caminho}")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.exists()
    with caminho.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        if novo:
            w.writerow(NOMES)
        w.writerow([_formatar(linha.get(n)) for n in NOMES])


def validar_arquivo(caminho: Path) -> list[str]:
    from analysis import schema

    return schema.validar(schema.carregar(caminho))
