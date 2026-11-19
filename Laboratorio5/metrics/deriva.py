"""Deriva documento × código (ARCHITECTURE.md).

doc_drift = regras do documento violadas pelo código + módulos do código que o
documento não menciona. Um módulo conta como mencionado quando seu nome aparece
no texto do documento como palavra inteira (ignorando maiúsculas).
"""

from __future__ import annotations

import re
from pathlib import Path

from metrics.arquitetura import Resultado
from metrics.java import Projeto, modulo

ARQUIVO = "ARCHITECTURE.md"


def modulos_do_codigo(p: Projeto) -> set[str]:
    return {modulo(a.pacote, p.pacote_base) for a in p.arquivos if modulo(a.pacote, p.pacote_base) != "(raiz)"}


def modulos_nao_documentados(p: Projeto, texto_doc: str) -> list[str]:
    ausentes = []
    for m in sorted(modulos_do_codigo(p)):
        # em "adapter.web" basta o documento citar o módulo completo ou o último segmento junto de "adapter"
        padroes = [re.escape(m)] + ([re.escape(m.split(".")[-1])] if "." in m else [])
        if not any(re.search(rf"(?<![\w]){pt}(?![\w])", texto_doc, re.I) for pt in padroes):
            ausentes.append(m)
    return ausentes


def medir(p: Projeto, arquitetura: Resultado) -> dict:
    doc = p.raiz / ARQUIVO
    if not doc.exists():
        # sem documento, nada do código está documentado e nenhuma regra foi declarada
        ausentes = sorted(modulos_do_codigo(p))
        return {"doc_drift": len(ausentes), "modulos_nao_documentados": ausentes, "regras_violadas": 0, "documento": False}
    ausentes = modulos_nao_documentados(p, doc.read_text(encoding="utf-8", errors="replace"))
    violadas = arquitetura.regras_violadas
    return {"doc_drift": violadas + len(ausentes), "modulos_nao_documentados": ausentes, "regras_violadas": violadas, "documento": True}
