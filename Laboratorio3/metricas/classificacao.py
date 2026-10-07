"""Classificação DORA: das notas por métrica à classe do repositório."""
from __future__ import annotations

import math
from typing import Sequence

from metricas.schemas import NOTAS_DORA

CLASSES = {nota: classe for classe, nota in NOTAS_DORA.items()}

# Um mês em semanas: as 52,1 semanas da janela divididas por 12. É o corte
# "1 por mês" da tabela, que a frequência (em releases por semana) compara.
SEMANAS_POR_MES = 4.34

HORAS_POR_DIA = 24.0
HORAS_POR_SEMANA = 7 * HORAS_POR_DIA
HORAS_POR_30_DIAS = 30 * HORAS_POR_DIA

METRICAS = ("freq", "lead_time", "cfr", "recuperacao")


def classificar_metrica(nome: str, valor: float) -> float:
    """Nota 1-4 de uma métrica, pelos cortes fixos da tabela de referência
    (ESPECIFICACAO.md, RQ 07). NaN entra e NaN sai: sem valor não há nota.

    Unidades de `valor`: `freq` em releases por semana; `lead_time` e
    `recuperacao` em horas; `cfr` em proporção 0-1. As bordas seguem a
    tabela: lead time e recuperação são "< corte" (o corte já é da classe
    pior); o CFR é "≤ corte" (o corte ainda é da classe melhor).
    """
    if nome not in METRICAS:
        raise ValueError(
            f"métrica desconhecida: {nome!r}. Use uma de {', '.join(METRICAS)}."
        )
    if valor is None or math.isnan(valor):
        return math.nan

    if nome == "freq":
        if valor >= 7:
            return 4
        if valor >= 1:
            return 3
        return 2 if valor >= 1 / SEMANAS_POR_MES else 1
    if nome == "lead_time":
        return _por_limite_superior(
            valor, (HORAS_POR_DIA, HORAS_POR_SEMANA, HORAS_POR_30_DIAS)
        )
    if nome == "recuperacao":
        return _por_limite_superior(valor, (1.0, HORAS_POR_DIA, HORAS_POR_SEMANA))
    # cfr: Elite ≤ 15%, High ≤ 30%, Medium ≤ 45%, Low acima.
    for corte, nota in ((0.15, 4), (0.30, 3), (0.45, 2)):
        if valor <= corte:
            return nota
    return 1


def _por_limite_superior(valor: float, cortes: tuple[float, float, float]) -> int:
    """4 abaixo do primeiro corte, 3 abaixo do segundo, 2 abaixo do terceiro."""
    for corte, nota in zip(cortes, (4, 3, 2)):
        if valor < corte:
            return nota
    return 1


def classificar_repo(notas: Sequence[float]) -> tuple[str | None, float]:
    """(classe_dora, classe_dora_nota) pela mediana das notas, para baixo.

    A mediana de um número par de notas pode cair entre duas classes
    ((3, 3, 2, 2) dá 2,5): arredonda-se para baixo, porque o repositório só
    ganha a classe que todas as métricas do meio sustentam.

    Aceita NaN, que é uma métrica que não pôde ser calculada: sai da conta em
    vez de puxar a mediana. Sem nenhuma nota, (None, NaN) — nenhuma classe é
    melhor que inventar uma.
    """
    validas = sorted(
        float(n) for n in notas
        if n is not None and not math.isnan(float(n))
    )
    if not validas:
        return None, math.nan
    for n in validas:
        if n not in CLASSES:
            raise ValueError(f"nota fora de 1-4: {n}")
    meio = len(validas) // 2
    mediana = (
        validas[meio] if len(validas) % 2
        else (validas[meio - 1] + validas[meio]) / 2
    )
    nota = int(math.floor(mediana))
    return CLASSES[nota], nota
