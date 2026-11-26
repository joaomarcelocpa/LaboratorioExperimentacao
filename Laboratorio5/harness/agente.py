"""Execucao nao interativa do Claude Code em um passo e leitura do que ele reporta.

Flags conferidas em `claude --help` (versao 2.1.238 instalada na maquina de desenvolvimento do harness; conferir de
novo na versao fixada em ambiente.pins): -p/--print, --model, --output-format stream-json (exige --verbose),
--permission-mode, --no-session-persistence, --setting-sources, --max-budget-usd.
`--max-turns` NAO aparece no --help dessa versao: so e passado se o --help da versao em uso o listar.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from harness.config import Config

# Comandos que contam como "o agente rodou testes por conta propria": o runner de testes do projeto (Maven)
# com fase de teste, ou um comando de teste explicito. `package`/`install` rodam testes salvo com -DskipTests.
_TESTE_MAVEN = re.compile(r"(?:\bmvn\b|\bmvnw\b|\./mvnw)\b[^\n|;&]*\b(test|verify|surefire:test|integration-test)\b")
_EMPACOTA = re.compile(r"(?:\bmvn\b|\bmvnw\b|\./mvnw)\b[^\n|;&]*\b(package|install)\b")
_SEM_TESTE = re.compile(r"-DskipTests|-Dmaven\.test\.skip")
_OUTROS_TESTES = re.compile(r"\b(pytest|npm\s+(run\s+)?test|npx\s+playwright\s+test|gradle\w*\s+test)\b|-Dtest=")


def comando_roda_testes(comando: str) -> bool:
    if _SEM_TESTE.search(comando):
        return False
    return bool(_TESTE_MAVEN.search(comando) or _EMPACOTA.search(comando) or _OUTROS_TESTES.search(comando))


@dataclass
class Resultado:
    ok: bool
    motivo: str  # "ok" | "tempo_esgotado" | "erro_do_agente" | "sem_resultado" | "falha_ao_iniciar"
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    turns: int | None = None
    duration_s: float = 0.0
    agent_ran_tests: int | None = None
    session_id: str | None = None
    transcript: Path | None = None
    comandos_de_teste: list[str] = field(default_factory=list)


def ler_transcript(caminho: Path) -> dict:
    """Extrai o evento final e os comandos Bash do stream-json. Linhas que nao sao JSON sao ignoradas."""
    final = None
    comandos: list[str] = []
    for linha in caminho.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha.startswith("{"):
            continue
        try:
            ev = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            final = ev
        elif ev.get("type") == "assistant":
            for bloco in (ev.get("message") or {}).get("content") or []:
                if isinstance(bloco, dict) and bloco.get("type") == "tool_use" and bloco.get("name") == "Bash":
                    cmd = (bloco.get("input") or {}).get("command")
                    if isinstance(cmd, str):
                        comandos.append(cmd)
    return {"final": final, "comandos": comandos}


def suporta_flag(cfg: Config, flag: str) -> bool:
    try:
        r = subprocess.run([*cfg.claude, "--help"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return flag in (r.stdout + r.stderr)


def montar_comando(cfg: Config, prompt: str) -> list[str]:
    cmd = [
        *cfg.claude, "-p", prompt,
        "--model", cfg.modelo,
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "bypassPermissions",
        "--no-session-persistence",
        "--setting-sources", "project",
    ]
    if cfg.max_budget_usd is not None:
        cmd += ["--max-budget-usd", str(cfg.max_budget_usd)]
    if cfg.max_turns is not None and suporta_flag(cfg, "--max-turns"):
        cmd += ["--max-turns", str(cfg.max_turns)]
    return cmd


def ambiente_do_agente(cfg: Config) -> dict[str, str]:
    env = dict(os.environ)
    env["DISABLE_AUTOUPDATER"] = "1"
    env["ANTHROPIC_MODEL"] = cfg.modelo
    return env


def comando_em_container(cfg: Config, workspace: Path, nome: str, interno: list[str]) -> list[str]:
    """Container descartavel: so o workspace e montado (nunca tests/acceptance nem reference), sem privilegios,
    com usuario do host para os arquivos voltarem com o dono certo. Credenciais entram so por variavel de ambiente."""
    return [
        "docker", "run", "--rm", "--name", nome,
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{workspace}:/work", "-w", "/work",
        "--tmpfs", "/tmp:exec", "-e", "HOME=/tmp/agente-home",
        "-e", "DISABLE_AUTOUPDATER=1", "-e", f"ANTHROPIC_MODEL={cfg.modelo}",
        "-e", "ANTHROPIC_API_KEY", "-e", "CLAUDE_CODE_OAUTH_TOKEN",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "4g", "--cpus", "2",
        cfg.imagem, *interno,
    ]


def executar(cfg: Config, workspace: Path, prompt: str, transcript: Path) -> Resultado:
    """Roda o agente uma vez (sessao nova) e grava o transcript sem nunca sobrescrever outro."""
    if transcript.exists():
        raise FileExistsError(f"transcript ja existe, dados brutos nunca sao sobrescritos: {transcript}")
    transcript.parent.mkdir(parents=True, exist_ok=True)
    interno = montar_comando(cfg, prompt)
    nome = f"lab05-agente-{uuid.uuid4().hex[:8]}"
    if cfg.container:
        cmd, cwd = comando_em_container(cfg, workspace, nome, interno), None
    else:
        cmd, cwd = interno, workspace
    env = ambiente_do_agente(cfg)
    inicio = time.monotonic()
    motivo = "ok"
    with transcript.open("xb") as saida, transcript.with_suffix(".stderr").open("xb") as erro:
        try:
            proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=saida, stderr=erro, timeout=cfg.timeout_s)
            if proc.returncode != 0:
                motivo = "erro_do_agente"
        except subprocess.TimeoutExpired:
            motivo = "tempo_esgotado"
            if cfg.container:
                subprocess.run(["docker", "kill", nome], capture_output=True)
        except OSError:
            motivo = "falha_ao_iniciar"
    duracao = time.monotonic() - inicio
    lido = ler_transcript(transcript)
    final = lido["final"]
    r = Resultado(ok=False, motivo=motivo, duration_s=round(duracao, 3), transcript=transcript)
    r.comandos_de_teste = [c for c in lido["comandos"] if comando_roda_testes(c)]
    r.agent_ran_tests = 1 if r.comandos_de_teste else 0
    if final is None:
        if motivo == "ok":
            r.motivo = "sem_resultado"
        return r
    uso = final.get("usage") or {}
    r.tokens_in = int(uso.get("input_tokens", 0)) + int(uso.get("cache_creation_input_tokens", 0)) \
        + int(uso.get("cache_read_input_tokens", 0))
    r.tokens_out = int(uso.get("output_tokens", 0))
    r.cost_usd = final.get("total_cost_usd")
    r.turns = final.get("num_turns")
    r.session_id = final.get("session_id")
    if motivo == "ok" and not final.get("is_error") and final.get("subtype") == "success":
        r.ok = True
    elif motivo == "ok":
        r.motivo = "erro_do_agente"
    return r
