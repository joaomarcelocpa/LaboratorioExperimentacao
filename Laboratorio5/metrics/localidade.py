"""Localidade da mudança: arquivos e módulos tocados pelo commit do passo.

files_touched: arquivos alterados no commit, sem saídas de build (target/, build/)
e sem documentos .md (a deriva documental é medida à parte).
modules_touched: módulos distintos dos arquivos Java de src/main/java no commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from metrics.java import DIR_FONTES, ler_arquivo, modulo

IGNORADOS = ("target/", "build/", ".git/", ".idea/", ".mvn/")


def _git(raiz: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def arquivos_do_commit(raiz: Path, commit: str = "HEAD") -> list[str]:
    """Caminhos alterados pelo commit (o primeiro commit conta tudo o que ele adiciona)."""
    saida = _git(raiz, "show", "--no-renames", "--relative", "--name-only", "--pretty=format:", commit)
    return [l for l in saida.splitlines() if l.strip()]


def medir(raiz: Path, pacote_base: str, commit: str = "HEAD") -> dict[str, int]:
    raiz = Path(raiz)
    arquivos = [a for a in arquivos_do_commit(raiz, commit) if not a.startswith(IGNORADOS) and not a.endswith(".md")]
    modulos = set()
    for a in arquivos:
        if a.startswith(str(DIR_FONTES)) and a.endswith(".java") and (raiz / a).exists():
            info = ler_arquivo(raiz / a)
            if info:
                modulos.add(modulo(info.pacote, pacote_base))
    return {"files_touched": len(arquivos), "modules_touched": len(modulos)}
