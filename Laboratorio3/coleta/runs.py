"""Coleta das execuções de CI do default branch.

A listagem de /actions/runs devolve no máximo 1.000 resultados por consulta,
então a janela é fatiada em meses e cada fatia que satura é partida ao meio
até caber. Partir um mês dá quinzenas; partir uma quinzena dá semanas.

As funções daqui produzem linhas já no formato dos contratos runs.csv e
run_attempts.csv. Quem escreve os CSVs é o orquestrador (#39), e quem calcula
CFR e tempo de recuperação é a #42.
"""
from __future__ import annotations

import logging
from collections import Counter

MAX_TENTATIVAS_PADRAO = 5

_log = logging.getLogger(__name__)

# Tabela da seção 3 do enunciado. O que não está aqui é ignorado — um
# conclusion novo não pode inflar o CFR sozinho.
_CLASSES = {
    "success": "sucesso",
    "failure": "falha",
    "timed_out": "falha",
    "startup_failure": "falha",
    "cancelled": "ignorado",
    "skipped": "ignorado",
    "neutral": "ignorado",
    "action_required": "ignorado",
    "stale": "ignorado",
}

_desconhecidas: Counter[str] = Counter()


def classificar(conclusion: str | None) -> str:
    """Sucesso, falha ou ignorado, pela tabela da seção 3.

    Tem um efeito colateral de propósito: valores fora da tabela são contados
    e o primeiro de cada um é logado. A alternativa, devolver
    (classe, desconhecido), contaminaria os chamadores da #42, que só querem
    a classe. O valor de retorno não depende do contador.
    """
    bruto = (conclusion or "").strip().lower()
    if not bruto:
        return "ignorado"
    if bruto in _CLASSES:
        return _CLASSES[bruto]
    if bruto not in _desconhecidas:
        _log.warning(
            "conclusion desconhecido na API: %r. Tratado como 'ignorado'. "
            "Se virar comum, acrescente a _CLASSES em coleta/runs.py.",
            bruto,
        )
    _desconhecidas[bruto] += 1
    return "ignorado"


def desconhecidas() -> dict[str, int]:
    """Valores de conclusion fora da tabela, com quantas vezes apareceram."""
    return dict(_desconhecidas)


def esquecer_desconhecidas() -> None:
    _desconhecidas.clear()
