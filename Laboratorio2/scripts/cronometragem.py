"""Cronometragem dos trials do Lab 2 (Sprint 1 - Tarefa 1).

Registra, por trial: integrante, kata, dificuldade, uso de IA, tempo gasto,
censura (estouro dos 35 min) e testes de aceitação que passaram.
"""

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path

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


CSV_HEADER = [
    "integrante",
    "kata",
    "dificuldade",
    "usou_ia",
    "tempo_segundos",
    "tempo_formatado",
    "censurado",
    "testes_passados",
    "data_hora",
]

DEFAULT_DADOS_DIR = Path(__file__).resolve().parent.parent / "dados"


def build_trial_row(
    integrante: str,
    kata: str,
    dificuldade: str,
    usou_ia: bool,
    tempo_segundos: float,
    censurado: bool,
    testes_passados: str,
    now: datetime,
) -> dict:
    return {
        "integrante": integrante,
        "kata": kata,
        "dificuldade": dificuldade,
        "usou_ia": "sim" if usou_ia else "nao",
        "tempo_segundos": int(round(tempo_segundos)),
        "tempo_formatado": format_duration(tempo_segundos),
        "censurado": "sim" if censurado else "nao",
        "testes_passados": int(testes_passados),
        "data_hora": now.isoformat(timespec="seconds"),
    }


def dados_path_for(integrante: str, base_dir: Path = DEFAULT_DADOS_DIR) -> Path:
    return Path(base_dir) / slugify(integrante) / "trials.csv"


def append_trial_to_csv(row: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
