"""Cronometragem dos trials do Lab 2 (Sprint 1 - Tarefa 1).

Registra, por trial: integrante, kata, dificuldade, uso de IA, tempo gasto,
censura (estouro dos 35 min) e testes de aceitação que passaram.
"""

import csv
import re
import time
import tkinter as tk
import unicodedata
from datetime import datetime
from pathlib import Path
from tkinter import ttk

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


class TrialApp:
    def __init__(self, root: tk.Tk, base_dir: Path = DEFAULT_DADOS_DIR, clock=time.monotonic):
        self.root = root
        self.base_dir = base_dir
        self.clock = clock
        self.start_time = None
        self.tempo_segundos = None
        self.censurado = False
        self.after_id = None

        root.title("Cronometragem de Trial — Lab 2")

        self.integrante_var = tk.StringVar()
        self.kata_var = tk.StringVar()
        self.dificuldade_var = tk.StringVar()
        self.usou_ia_var = tk.BooleanVar()
        self.testes_var = tk.StringVar()
        self.status_var = tk.StringVar(value="")
        self.timer_var = tk.StringVar(value="00:00")
        self.erro_var = tk.StringVar(value="")

        self._build_form_widgets()
        self._build_timer_widgets()
        self._build_finish_widgets()
        self._show_form_state()

    def _build_form_widgets(self):
        frame = ttk.Frame(self.root, padding=12)
        self.form_frame = frame

        ttk.Label(frame, text="Integrante").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.integrante_var).grid(row=0, column=1, sticky="ew")

        ttk.Label(frame, text="Kata").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.kata_var).grid(row=1, column=1, sticky="ew")

        ttk.Label(frame, text="Dificuldade").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            frame, textvariable=self.dificuldade_var, values=DIFICULDADES, state="readonly"
        ).grid(row=2, column=1, sticky="ew")

        ttk.Checkbutton(frame, text="Usou IA?", variable=self.usou_ia_var).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )

        self.iniciar_btn = ttk.Button(frame, text="Iniciar", command=self.start_trial, state="disabled")
        self.iniciar_btn.grid(row=4, column=0, columnspan=2, pady=8)

        for var in (self.integrante_var, self.kata_var, self.dificuldade_var):
            var.trace_add("write", lambda *_: self._update_iniciar_state())

    def _update_iniciar_state(self):
        campos_ok = (
            bool(self.integrante_var.get().strip())
            and bool(self.kata_var.get().strip())
            and self.dificuldade_var.get() in DIFICULDADES
        )
        self.iniciar_btn.configure(state="normal" if campos_ok else "disabled")

    def _build_timer_widgets(self):
        frame = ttk.Frame(self.root, padding=12)
        self.timer_frame = frame
        ttk.Label(frame, textvariable=self.timer_var, font=("Segoe UI", 32)).grid(row=0, column=0)
        ttk.Button(frame, text="Parar", command=self.stop_trial).grid(row=1, column=0, pady=8)

    def _build_finish_widgets(self):
        frame = ttk.Frame(self.root, padding=12)
        self.finish_frame = frame
        ttk.Label(frame, textvariable=self.status_var).grid(row=0, column=0, columnspan=2)
        ttk.Label(frame, text="Testes de aceitação que passaram").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.testes_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(frame, textvariable=self.erro_var, foreground="red").grid(row=2, column=0, columnspan=2)
        ttk.Button(frame, text="Salvar", command=self.save_trial).grid(row=3, column=0, columnspan=2, pady=8)

    def _show_form_state(self):
        self.timer_frame.grid_forget()
        self.finish_frame.grid_forget()
        self.form_frame.grid(row=0, column=0, sticky="nsew")
        self.integrante_var.set("")
        self.kata_var.set("")
        self.dificuldade_var.set("")
        self.usou_ia_var.set(False)
        self.testes_var.set("")
        self.erro_var.set("")
        self.status_var.set("")
        self._update_iniciar_state()

    def _show_timer_state(self):
        self.form_frame.grid_forget()
        self.timer_frame.grid(row=0, column=0, sticky="nsew")

    def _show_finish_state(self):
        self.timer_frame.grid_forget()
        self.finish_frame.grid(row=0, column=0, sticky="nsew")

    def start_trial(self):
        self.start_time = self.clock()
        self.censurado = False
        self._show_timer_state()
        self._tick()

    def _tick(self):
        elapsed = self.clock() - self.start_time
        if is_censored(elapsed):
            self._finish_trial(tempo_segundos=TIME_LIMIT_SECONDS, censurado=True)
            return
        self.timer_var.set(format_duration(elapsed))
        self.after_id = self.root.after(1000, self._tick)

    def stop_trial(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        elapsed = self.clock() - self.start_time
        self._finish_trial(tempo_segundos=elapsed, censurado=is_censored(elapsed))

    def _finish_trial(self, tempo_segundos, censurado):
        self.tempo_segundos = tempo_segundos
        self.censurado = censurado
        self.timer_var.set(format_duration(tempo_segundos))
        texto = f"Tempo: {format_duration(tempo_segundos)}"
        if censurado:
            texto += " — CENSURADO (35 min)"
        self.status_var.set(texto)
        self._show_finish_state()

    def save_trial(self):
        errors = validate_trial_form(
            self.integrante_var.get(),
            self.kata_var.get(),
            self.dificuldade_var.get(),
            self.testes_var.get(),
        )
        if errors:
            self.erro_var.set(" ".join(errors))
            return

        row = build_trial_row(
            integrante=self.integrante_var.get().strip(),
            kata=self.kata_var.get().strip(),
            dificuldade=self.dificuldade_var.get(),
            usou_ia=self.usou_ia_var.get(),
            tempo_segundos=self.tempo_segundos,
            censurado=self.censurado,
            testes_passados=self.testes_var.get(),
            now=datetime.now(),
        )
        path = dados_path_for(row["integrante"], self.base_dir)
        append_trial_to_csv(row, path)
        salvo_em = str(path)
        self._show_form_state()
        self.status_var.set(f"Trial salvo em {salvo_em}")


def main():
    root = tk.Tk()
    TrialApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
