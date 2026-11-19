"""Percentual de duplicação (jscpd) sobre src/main/java."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from metrics.java import DIR_FONTES

MIN_TOKENS = 50
MIN_LINHAS = 5


def medir(raiz: Path, min_tokens: int = MIN_TOKENS, min_linhas: int = MIN_LINHAS, npx: str = "npx") -> float:
    fontes = Path(raiz) / DIR_FONTES
    if not any(fontes.rglob("*.java")):
        return 0.0
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [npx, "--yes", "jscpd", "--silent", "--format", "java", "--reporters", "json", "--output", tmp,
               "--min-tokens", str(min_tokens), "--min-lines", str(min_linhas), "--ignore", "**/target/**", str(fontes)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        relatorio = Path(tmp) / "jscpd-report.json"
        if not relatorio.exists():
            raise RuntimeError(f"jscpd não gerou relatório: {r.stderr.strip() or r.stdout.strip()}")
        total = json.loads(relatorio.read_text())["statistics"]["total"]
    return round(float(total.get("percentage", 0.0)), 2)


def versao(npx: str = "npx") -> str:
    r = subprocess.run([npx, "--yes", "jscpd", "--version"], capture_output=True, text=True)
    return r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "desconhecida"
