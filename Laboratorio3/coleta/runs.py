"""Coleta das execuções de CI do default branch.

A listagem de /actions/runs devolve no máximo 1.000 resultados por consulta,
então a janela é fatiada em meses e cada fatia que satura é partida ao meio
até caber. Partir um mês dá quinzenas; partir uma quinzena dá semanas.

As funções daqui produzem linhas já no formato dos contratos runs.csv e
run_attempts.csv. Quem escreve os CSVs é o orquestrador (#39), e quem calcula
CFR e tempo de recuperação é a #42.
"""
from __future__ import annotations

import calendar
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

MAX_TENTATIVAS_PADRAO = 5
TETO_POR_CONSULTA = 1000          # máximo de resultados por consulta filtrada
PISO_DA_FATIA = timedelta(hours=1)

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


def iso(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _comeco(dia: date) -> datetime:
    return datetime.combine(dia, time(0, 0, 0), tzinfo=timezone.utc)


def _fim(dia: date) -> datetime:
    return datetime.combine(dia, time(23, 59, 59), tzinfo=timezone.utc)


@dataclass(frozen=True)
class Fatia:
    """Intervalo fechado nas duas pontas: [inicio, fim]."""

    inicio: datetime
    fim: datetime

    def duracao(self) -> timedelta:
        # +1 s porque o fim é fechado: 00:00:00..00:59:59 é uma hora cheia.
        return self.fim - self.inicio + timedelta(seconds=1)

    def e_de_dias_inteiros(self) -> bool:
        return (
            self.inicio.time() == time(0, 0, 0)
            and self.fim.time() == time(23, 59, 59)
        )

    def created(self) -> str:
        """Valor do parâmetro created= da API.

        A forma de data é a do enunciado e é a que a API aceita com certeza;
        a forma com hora só aparece abaixo de um dia, quando a subdivisão
        precisa descer mais.
        """
        if self.e_de_dias_inteiros():
            return f"{self.inicio.date().isoformat()}..{self.fim.date().isoformat()}"
        return f"{iso(self.inicio)}..{iso(self.fim)}"

    def partir(self) -> tuple["Fatia", "Fatia"] | None:
        """Duas metades sem buraco e sem sobreposição, ou None no piso."""
        if self.duracao() <= PISO_DA_FATIA:
            return None
        meio = (self.inicio + self.duracao() / 2).replace(microsecond=0)
        if meio <= self.inicio or meio > self.fim:
            return None
        return (
            Fatia(self.inicio, meio - timedelta(seconds=1)),
            Fatia(meio, self.fim),
        )


def meses(inicio: date, fim: date) -> list[Fatia]:
    """A janela em fatias de mês-calendário, recortadas nas pontas.

    O recorte importa: uma janela que começa no dia 15 não pode render uma
    fatia que começa no dia 1, senão a coleta puxa runs de fora da janela e
    enviesa a amostra inteira.
    """
    if fim < inicio:
        raise ValueError(f"fim ({fim}) é anterior a inicio ({inicio})")

    fatias: list[Fatia] = []
    atual = inicio
    while atual <= fim:
        ultimo_do_mes = atual.replace(
            day=calendar.monthrange(atual.year, atual.month)[1]
        )
        fatias.append(Fatia(_comeco(atual), _fim(min(ultimo_do_mes, fim))))
        atual = ultimo_do_mes + timedelta(days=1)
    return fatias
