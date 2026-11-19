"""Constrói workspaces Java pequenos (hexagonal) e commitados, para testar as métricas."""

from __future__ import annotations

import subprocess
from pathlib import Path

BASE = "com.exemplo.tarefas"
RAIZ_JAVA = "src/main/java/com/exemplo/tarefas"

LIMPO = {
    "domain/Tarefa.java": "package com.exemplo.tarefas.domain;\npublic class Tarefa {\n  public String titulo;\n  public int peso(int x) { if (x > 0) { return x; } return 0; }\n}\n",
    "domain/TarefaPort.java": "package com.exemplo.tarefas.domain;\npublic interface TarefaPort { Tarefa buscar(String id); }\n",
    "application/CriarTarefa.java": "package com.exemplo.tarefas.application;\nimport com.exemplo.tarefas.domain.Tarefa;\nimport com.exemplo.tarefas.domain.TarefaPort;\nimport java.util.List;\npublic class CriarTarefa {\n  public Tarefa criar(TarefaPort p) { return p.buscar(\"1\"); }\n}\n",
    "adapter/web/TarefaController.java": "package com.exemplo.tarefas.adapter.web;\nimport com.exemplo.tarefas.application.CriarTarefa;\npublic class TarefaController { CriarTarefa uc; }\n",
    "adapter/persistence/TarefaAdapter.java": "package com.exemplo.tarefas.adapter.persistence;\nimport com.exemplo.tarefas.domain.Tarefa;\nimport com.exemplo.tarefas.domain.TarefaPort;\npublic class TarefaAdapter implements TarefaPort { public Tarefa buscar(String id) { return null; } }\n",
}

ARCHITECTURE_COMPLETA = """# Arquitetura
Hexagonal. Módulos: domain, application, adapter.web, adapter.persistence.
Regras: domain não depende de nada; application só de domain.
"""


def _git(raiz: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=raiz, check=True, capture_output=True)


def criar_workspace(raiz: Path, arquivos: dict[str, str] | None = None, extras: dict[str, str] | None = None,
                    architecture: str | None = ARCHITECTURE_COMPLETA, commitar: bool = True) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    mapa = dict(LIMPO if arquivos is None else arquivos)
    mapa.update(extras or {})
    for rel, conteudo in mapa.items():
        destino = raiz / RAIZ_JAVA / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo)
    if architecture is not None:
        (raiz / "ARCHITECTURE.md").write_text(architecture)
    if commitar:
        _git(raiz, "init", "-q")
        _git(raiz, "add", "-A")
        _git(raiz, "commit", "-q", "-m", "passo 0")
    return raiz


def novo_commit(raiz: Path, extras: dict[str, str], mensagem: str = "passo") -> None:
    for rel, conteudo in extras.items():
        destino = raiz / (RAIZ_JAVA + "/" + rel if not rel.startswith(("src/", "pom", "README")) else rel)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo)
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", mensagem)
