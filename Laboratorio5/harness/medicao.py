"""Medicao de um passo: build, subida, testes (duas rodadas) e metricas estruturais.

`Medidor` e a implementacao real (Maven, docker compose, metrics/). Os testes do harness usam um medidor falso
com a mesma interface. Falha de infraestrutura (Maven sem relatorios, por exemplo) levanta `ErroDeInfra` e NAO
gera linha de dados: um numero errado no CSV seria pior que um passo nao registrado.

Ganchos por variavel de ambiente (HARNESS_CMD_BUILD, _SUBIR, _DESCER, _REGRESSAO, _ACEITACAO): trocam o comando
padrao. Existem so para testar o harness sem Docker; a coleta usa os padroes.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from harness.config import Config


class ErroDeInfra(Exception):
    pass


def ler_relatorios(pasta: Path) -> dict[str, bool]:
    """Resultado por teste (nome qualificado -> passou) dos relatorios surefire em `pasta`."""
    resultados: dict[str, bool] = {}
    for xml in sorted(pasta.glob("TEST-*.xml")):
        for caso in ET.parse(xml).getroot().iter("testcase"):
            if caso.find("skipped") is not None:
                continue
            nome = f"{caso.get('classname')}.{caso.get('name')}"
            resultados[nome] = caso.find("failure") is None and caso.find("error") is None
    return resultados


def contar_rodadas(rodada1: dict[str, bool], rodada2: dict[str, bool]) -> dict[str, int]:
    """Definicao do protocolo: falha = falha nas DUAS rodadas; flaky = resultado diferente entre as rodadas."""
    nomes = set(rodada1) | set(rodada2)
    falhou1 = {n for n in nomes if rodada1.get(n) is False}
    falhou2 = {n for n in nomes if rodada2.get(n) is False}
    return {"total": len(nomes), "failed": len(falhou1 & falhou2), "flaky": len(falhou1 ^ falhou2)}


def medir_testes(medidor, pedido: str | None) -> dict[str, int]:
    """reg_total, reg_failed, acc_total, acc_failed e flaky (regressao + aceitacao do pedido atual)."""
    reg = contar_rodadas(medidor.regressao(), medidor.regressao())
    if pedido is None:
        acc = {"total": 0, "failed": 0, "flaky": 0}
    else:
        acc = contar_rodadas(medidor.aceitacao(pedido), medidor.aceitacao(pedido))
        if acc["total"] == 0:
            raise ErroDeInfra(f"nenhum teste de aceitacao encontrado para {pedido}: suite vazia passaria em silencio")
    return {"reg_total": reg["total"], "reg_failed": reg["failed"], "acc_total": acc["total"],
            "acc_failed": acc["failed"], "flaky": reg["flaky"] + acc["flaky"]}


class Medidor:
    def __init__(self, cfg: Config, leve: bool = False):
        self.cfg = cfg
        self.leve = leve  # so para testar o harness: pula ArchUnit, jdeps e jscpd (colunas ficam invalidas)
        self.workspace: Path | None = None

    # -- utilitarios ------------------------------------------------------------------------------------------
    def _cmd(self, nome: str, padrao: list[str]) -> list[str]:
        custom = os.environ.get(f"HARNESS_CMD_{nome}")
        return shlex.split(custom) if custom else padrao

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["BASE_URL"] = self.cfg.base_url
        return env

    def _rodar(self, cmd: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(cmd, cwd=cwd, env=self._env(), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise ErroDeInfra(f"tempo esgotado em {' '.join(cmd)}") from e
        except OSError as e:
            raise ErroDeInfra(f"nao foi possivel executar {cmd[0]}: {e}") from e

    # -- build e subida ----------------------------------------------------------------------------------------
    def construir(self, ws: Path) -> bool:
        """build_ok: o projeto compila e empacota (sem rodar testes)."""
        r = self._rodar(self._cmd("BUILD", ["mvn", "-B", "-q", "-DskipTests", "package"]), ws)
        return r.returncode == 0

    def _compose(self, ws: Path, *args: str) -> list[str]:
        arquivos = ["-f", "docker-compose.yml"]
        if self.cfg.compose_override:
            arquivos += ["-f", str(self.cfg.lab / "harness" / "container" / "compose.override.yml")]
        return ["docker", "compose", "-p", self.cfg.projeto_compose, *arquivos, *args]

    def subir(self, ws: Path) -> bool:
        """boot_ok: `docker compose up` sobe e GET /health responde 200 dentro do prazo (contrato de execucao)."""
        self.workspace = ws
        r = self._rodar(self._cmd("SUBIR", self._compose(ws, "up", "-d", "--build")), ws)
        if r.returncode != 0:
            return False
        fim = time.monotonic() + self.cfg.espera_saude_s
        while time.monotonic() < fim:
            try:
                with urllib.request.urlopen(f"{self.cfg.base_url}/health", timeout=3) as resp:
                    if resp.status == 200:
                        return True
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(2)
        return False

    def descer(self, ws: Path | None = None) -> None:
        ws = ws or self.workspace
        if ws is None:
            return
        self._rodar(self._cmd("DESCER", self._compose(ws, "down", "-v", "--remove-orphans")), ws)

    # -- testes -------------------------------------------------------------------------------------------------
    def _suite(self, nome_cmd: str, pasta: Path, extra: list[str]) -> dict[str, bool]:
        relatorios = pasta / "target" / "surefire-reports"
        if relatorios.exists():
            for antigo in relatorios.glob("TEST-*.xml"):
                antigo.unlink()
        r = self._rodar(self._cmd(nome_cmd, ["mvn", "-B", "-q", "test", *extra]), pasta)
        resultados = ler_relatorios(relatorios)
        if not resultados:
            raise ErroDeInfra(f"sem relatorios de teste em {relatorios}: {(r.stdout + r.stderr)[-800:]}")
        return resultados

    def regressao(self) -> dict[str, bool]:
        return self._suite("REGRESSAO", self.cfg.lab / "tests" / "regression", [])

    def aceitacao(self, pedido: str) -> dict[str, bool]:
        # um padrao por pacote: "P1*Test" casaria tambem P10BancoTest
        filtro = f"-Dtest=**/{pedido.lower()}/*Test"
        return self._suite("ACEITACAO", self.cfg.lab / "tests" / "acceptance",
                           [filtro, "-Dsurefire.failIfNoSpecifiedTests=false"])

    # -- produto ------------------------------------------------------------------------------------------------
    def produto(self, ws: Path, commit: str = "HEAD") -> dict:
        """Colunas 24 a 31 via metrics/coletar.py (as mesmas funcoes do `python -m metrics.coletar`)."""
        from metrics.coletar import coletar

        return coletar(ws, commit, com_jscpd=not self.leve, com_archunit=not self.leve, com_jdeps=not self.leve)
