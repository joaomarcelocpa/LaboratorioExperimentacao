"""Workspace de uma cadeia: copia da semente em um repositorio versionado, um commit por passo.

O workspace fica FORA do repositorio do laboratorio (em HARNESS_WORK), para o agente nunca ver tests/acceptance
nem reference. `verificar_isolamento` confere isso antes de cada execucao.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from harness.config import PASTAS_OCULTAS

_VCS = ["git", "-c", "user.name=harness", "-c", "user.email=harness@local", "-c", "commit.gpgsign=false"]
_IGNORAR = shutil.ignore_patterns("target", ".git", ".idea", "*.iml")


class IsolamentoViolado(Exception):
    pass


def _vcs(ws: Path, *args: str) -> str:
    r = subprocess.run([*_VCS, *args], cwd=ws, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"comando de versionamento falhou ({' '.join(args)}): {r.stderr.strip()}")
    return r.stdout.strip()


def head(ws: Path) -> str:
    return _vcs(ws, "rev-parse", "HEAD")


def contar_commits(ws: Path) -> int:
    return int(_vcs(ws, "rev-list", "--count", "HEAD"))


def verificar_isolamento(ws: Path, ocultas: tuple[Path, ...] = PASTAS_OCULTAS) -> None:
    """O workspace nao pode conter, nem estar dentro de, os testes ocultos e a referencia."""
    ws = ws.resolve()
    for oculta in ocultas:
        o = oculta.resolve()
        if ws == o or o in ws.parents or ws in o.parents:
            raise IsolamentoViolado(f"{ws} se sobrepoe a {o}")
    for nome in ("acceptance", "reference"):
        achou = [p for p in ws.rglob(nome) if ".git" not in p.parts and p.is_dir()]
        if achou:
            raise IsolamentoViolado(f"pasta oculta dentro do workspace: {achou[0]}")


def preparar(seed: Path, destino: Path, mensagem: str = "passo 0: semente") -> str:
    if destino.exists():
        raise FileExistsError(f"workspace ja existe: {destino}")
    shutil.copytree(seed, destino, ignore=_IGNORAR)
    _vcs(destino, "init", "-q", "-b", "main")
    _vcs(destino, "add", "-A")
    _vcs(destino, "commit", "-q", "-m", mensagem)
    verificar_isolamento(destino)
    return head(destino)


def fechar_passo(ws: Path, base: str, mensagem: str) -> str:
    """Um commit por passo: junta em um unico commit sobre `base` tudo o que o agente deixou, inclusive commits
    que ele mesmo tenha feito (reset --soft). A arvore de arquivos nao muda."""
    _vcs(ws, "reset", "-q", "--soft", base)
    _vcs(ws, "add", "-A")
    _vcs(ws, "commit", "-q", "--allow-empty", "-m", mensagem)
    return head(ws)


def restaurar(ws: Path, base: str, raiz_permitida: Path) -> None:
    """Volta ao estado `base` para a nova tentativa. So age dentro da pasta de trabalho do harness."""
    ws, raiz = ws.resolve(), raiz_permitida.resolve()
    if raiz not in ws.parents:
        raise IsolamentoViolado(f"recusa limpar {ws}: fora de {raiz}")
    _vcs(ws, "reset", "-q", "--hard", base)
    _vcs(ws, "clean", "-q", "-fdx")
