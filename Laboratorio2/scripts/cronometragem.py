"""Cronometragem dos trials do Lab 2 (Sprint 1 - Tarefa 1).

Registra, por trial: integrante, kata, dificuldade, uso de IA, tempo gasto,
censura (estouro dos 35 min) e testes de aceitação que passaram.
"""

import re
import unicodedata

TIME_LIMIT_SECONDS = 35 * 60


def is_censored(elapsed_seconds: float, limit_seconds: int = TIME_LIMIT_SECONDS) -> bool:
    return elapsed_seconds >= limit_seconds


def format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


DIFICULDADES = ["facil", "medio", "dificil"]


def slugify(nome: str) -> str:
    normalized = unicodedata.normalize("NFKD", nome.strip().lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_")
    return slug or "integrante"


def validate_trial_form(integrante: str, kata: str, dificuldade: str, testes_passados: str) -> list[str]:
    errors = []
    if not integrante.strip():
        errors.append("Integrante é obrigatório.")
    if not kata.strip():
        errors.append("Kata é obrigatório.")
    if dificuldade not in DIFICULDADES:
        errors.append("Dificuldade deve ser facil, medio ou dificil.")
    try:
        valor = int(testes_passados)
        if valor < 0:
            errors.append("Testes passados não pode ser negativo.")
    except (TypeError, ValueError):
        errors.append("Testes passados deve ser um número inteiro.")
    return errors
