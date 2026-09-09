"""Cronometragem dos trials do Lab 2 (Sprint 1 - Tarefa 1).

Registra, por trial: integrante, kata, dificuldade, uso de IA, tempo gasto,
censura (estouro dos 35 min) e testes de aceitação que passaram.
"""

TIME_LIMIT_SECONDS = 35 * 60


def is_censored(elapsed_seconds: float, limit_seconds: int = TIME_LIMIT_SECONDS) -> bool:
    return elapsed_seconds >= limit_seconds


def format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"
