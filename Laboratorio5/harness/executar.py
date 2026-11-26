"""Orquestra cadeias do experimento: protocolo por passo (planejamento, secao 3.5) gravando uma linha por passo.

    python -m harness.executar cadeia --cadeia 1 --modo incremental --executar
    python -m harness.executar piloto --executar        # 3 cadeias x 2 modos x P1..P4 = 24 execucoes

Sem --executar o comando so mostra o que faria. O agente SO roda com --executar (custa dinheiro e tempo).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from analysis.schema import MODOS
from harness import agente, csvpassos, pedidos as ped, workspace
from harness.config import Config
from harness.medicao import ErroDeInfra, Medidor, medir_testes

PEDIDOS_PILOTO = ["P1", "P2", "P3", "P4"]
CADEIAS_PILOTO = 3


def agora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tipo_do_pedido(cfg: Config, pedido_id: str) -> str:
    cabecalho = ped.arquivo(cfg, pedido_id).read_text(encoding="utf-8").split("---", 1)[0]
    m = re.search(r"\*\*Tipo:\*\*\s*(\w+)", cabecalho)
    if not m:
        raise ped.PedidoInexistente(f"{pedido_id}: sem '**Tipo:**' no cabecalho")
    palavra = m.group(1).lower()
    if palavra not in ("cabe", "tensiona"):
        raise ped.PedidoInexistente(f"{pedido_id}: tipo desconhecido '{palavra}'")
    return palavra


def versao_do_claude(cfg: Config) -> str:
    """Versao de `claude --version` (primeiro token). Em modo container a versao e a da imagem, fixada no pin."""
    if cfg.container and cfg.versao_claude:
        return cfg.versao_claude
    r = subprocess.run([*cfg.claude, "--version"], capture_output=True, text=True, timeout=60)
    saida = (r.stdout or "").split()
    if r.returncode != 0 or not saida:
        raise ErroDeInfra(f"nao consegui ler a versao do Claude Code: {r.stderr.strip()}")
    return saida[0]


@dataclass
class Contexto:
    cfg: Config
    medidor: object
    saida: Path
    pedidos: list[str]
    agora: Callable[[], str] = agora_utc

    @property
    def log(self) -> Path:
        return self.cfg.resultados / "execucoes.jsonl"

    def registrar(self, **registro) -> None:
        """Log bruto de tudo o que aconteceu (inclui tentativas e custos da 1a tentativa). So acrescenta."""
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


def _linha_base(ctx: Contexto, chain: int, modo: str, passo: int, pedido: str, tipo: str, versao: str) -> dict:
    return {"chain_id": chain, "mode": modo, "step": passo, "request_id": pedido, "request_type": tipo,
            "tool_version": versao, "model_id": ctx.cfg.modelo}


def _medir_estado(ctx: Contexto, ws: Path, pedido: str | None, build_ok: int) -> dict:
    """boot, duas rodadas de regressao e de aceitacao e metricas do produto, no estado atual do workspace."""
    m = ctx.medidor
    boot_ok = 0
    try:
        boot_ok = int(m.subir(ws))
        testes = medir_testes(m, pedido)
    finally:
        m.descer(ws)
    produto = m.produto(ws, "HEAD")
    medidas = {"build_ok": build_ok, "boot_ok": boot_ok, **testes,
               **{k: produto[k] for k in ("arch_violations", "cycles", "files_touched", "modules_touched",
                                           "max_ccn", "dup_pct", "loc", "doc_drift")}}
    return {"medidas": medidas, "detalhe": produto.get("detalhe")}


def _ws_do_passo(ctx: Contexto, base: Path, modo: str, passo: int) -> Path:
    return base / ("ws" if modo == "incremental" else f"ws-p{passo}")


def rodar_cadeia(ctx: Contexto, chain: int, modo: str) -> str:
    """Executa (ou retoma) uma cadeia. Devolve 'completa', 'censurada' ou 'ja_completa'."""
    cfg = ctx.cfg
    base = cfg.work_root / f"{modo}-c{chain:02d}"
    versao = versao_do_claude(cfg)
    existentes = csvpassos.da_cadeia(ctx.saida, chain, modo)
    if existentes:
        if existentes[-1]["status"] == "falha":
            return "ja_completa"
        if int(existentes[-1]["step"]) >= len(ctx.pedidos):
            return "ja_completa"
        if modo == "incremental":
            ws = base / "ws"
            if not ws.exists() or workspace.contar_commits(ws) != len(existentes):
                raise ErroDeInfra(
                    f"cadeia {chain}/{modo} tem {len(existentes)} linhas mas o workspace nao confere; dados "
                    "brutos nao se sobrescrevem: registre como desvio e use outro chain_id")
        primeiro = len(existentes)
    else:
        ws0 = _ws_do_passo(ctx, base, modo, 0)
        workspace.preparar(cfg.seed, ws0)
        if not ctx.medidor.construir(ws0):
            raise ErroDeInfra("a semente nao compila: nao ha linha-base valida")
        medido = _medir_estado(ctx, ws0, None, 1)
        linha = _linha_base(ctx, chain, modo, 0, "P0", "semente", versao)
        linha.update(medido["medidas"], timestamp=ctx.agora(), run_ok=1, retry=0, status="ok")
        csvpassos.anexar(ctx.saida, linha)
        ctx.registrar(evento="passo0", chain=chain, modo=modo, medicao=medido["medidas"], detalhe=medido["detalhe"])
        primeiro = 1

    for passo in range(primeiro, len(ctx.pedidos) + 1):
        pedido = ctx.pedidos[passo - 1]
        ws = _ws_do_passo(ctx, base, modo, passo)
        if modo == "regenerado":
            base_commit = workspace.preparar(cfg.seed, ws, f"semente (passo {passo}, regenerado)")
        else:
            base_commit = workspace.head(ws)
        prompt = ped.prompt_do_passo(cfg, modo, ctx.pedidos, passo)

        final = None
        for tentativa in (1, 2):
            transcript = cfg.resultados / "transcripts" / f"{modo}-c{chain:02d}-p{passo:02d}-t{tentativa}.jsonl"
            workspace.verificar_isolamento(ws)
            res = agente.executar(cfg, ws, prompt, transcript)
            build_ok = 0
            commit = None
            if res.ok:
                commit = workspace.fechar_passo(ws, base_commit, f"passo {passo}: {pedido}")
                build_ok = int(ctx.medidor.construir(ws))
            ctx.registrar(evento="tentativa", chain=chain, modo=modo, passo=passo, pedido=pedido,
                          tentativa=tentativa, ok=res.ok, motivo=res.motivo, build_ok=build_ok, commit=commit,
                          tokens_in=res.tokens_in, tokens_out=res.tokens_out, cost_usd=res.cost_usd,
                          turns=res.turns, duration_s=res.duration_s, agent_ran_tests=res.agent_ran_tests,
                          comandos_de_teste=res.comandos_de_teste, session_id=res.session_id,
                          transcript=str(transcript), timestamp=ctx.agora())
            final = (tentativa, res, build_ok)
            if res.ok and build_ok:
                break
            if tentativa == 1:
                # nova tentativa a partir do MESMO estado e sem feedback do erro
                workspace.restaurar(ws, base_commit, cfg.work_root)

        tentativa, res, build_ok = final
        linha = _linha_base(ctx, chain, modo, passo, pedido, tipo_do_pedido(cfg, pedido), versao)
        linha.update(timestamp=ctx.agora(), tokens_in=res.tokens_in, tokens_out=res.tokens_out, cost_usd=res.cost_usd,
                     duration_s=res.duration_s, turns=res.turns, agent_ran_tests=res.agent_ran_tests,
                     run_ok=int(res.ok), retry=int(tentativa == 2), build_ok=build_ok)
        if not (res.ok and build_ok):
            # falha de passo: medidas do produto vazias, a cadeia termina e o dado e censurado
            linha.update(status="falha", build_ok=0)
            csvpassos.anexar(ctx.saida, linha)
            ctx.registrar(evento="cadeia_censurada", chain=chain, modo=modo, passo=passo, motivo=res.motivo)
            return "censurada"
        medido = _medir_estado(ctx, ws, pedido, build_ok)
        linha.update(medido["medidas"], status="ok")
        csvpassos.anexar(ctx.saida, linha)
        ctx.registrar(evento="medicao", chain=chain, modo=modo, passo=passo, medicao=medido["medidas"],
                      detalhe=medido["detalhe"])
    return "completa"


def verificar_ambiente(cfg: Config, maquina: str) -> None:
    saida = cfg.resultados / f"ambiente-{maquina}-{datetime.now(timezone.utc):%Y%m%d}.json"
    r = subprocess.run([str(cfg.lab / "harness" / "check-env"), "--maquina", maquina, "--saida", str(saida),
                        "--workspace", str(cfg.work_root)], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        raise ErroDeInfra("ambiente nao conforme (harness/check-env): corrija antes de executar")


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    for nome in ("cadeia", "piloto"):
        s = sub.add_parser(nome)
        s.add_argument("--executar", action="store_true", help="roda de verdade (sem isso, so mostra o plano)")
        s.add_argument("--pedidos", default=",".join(PEDIDOS_PILOTO))
        s.add_argument("--saida", type=Path, default=None, help="CSV por passo (padrao: results/pilot/passos.csv)")
        s.add_argument("--sem-container", action="store_true", help="SO para testar o harness: agente no host")
        s.add_argument("--sem-check-env", action="store_true", help="SO para testar o harness")
        s.add_argument("--leve", action="store_true", help="SO para testar o harness: pula ArchUnit/jdeps/jscpd")
        s.add_argument("--maquina", default="?")
        if nome == "cadeia":
            s.add_argument("--cadeia", type=int, required=True)
            s.add_argument("--modo", choices=MODOS, required=True)
        else:
            s.add_argument("--cadeias", type=int, default=CADEIAS_PILOTO)
    return p.parse_args(argv)


def principal(argv: list[str] | None = None) -> int:
    a = _argumentos(argv)
    cfg = Config.do_ambiente(container=not a.sem_container)
    cfg.compose_override = "P9" in a.pedidos.replace(" ", "").split(",")
    saida = a.saida or cfg.resultados / "passos.csv"
    lista = [x.strip() for x in a.pedidos.split(",") if x.strip()]
    if a.comando == "cadeia":
        plano = [(a.cadeia, a.modo)]
    else:
        plano = [(c, m) for c in range(1, a.cadeias + 1) for m in MODOS]
    print(f"{len(plano)} cadeia(s) x {len(lista)} pedido(s) = {len(plano) * len(lista)} execucao(oes) do agente")
    for c, m in plano:
        print(f"  cadeia {c} modo {m}: {', '.join(lista)}")
    if not a.executar:
        print("nada foi executado (use --executar; cada execucao consome o plano do Claude Code)")
        return 0
    try:
        if not a.sem_check_env:
            verificar_ambiente(cfg, a.maquina)
        ctx = Contexto(cfg, Medidor(cfg, leve=a.leve), saida, lista)
        for c, m in plano:
            print(f"== cadeia {c} / {m}: {rodar_cadeia(ctx, c, m)}")
    except (ErroDeInfra, workspace.IsolamentoViolado, ped.PedidoInexistente) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    problemas = csvpassos.validar_arquivo(saida)
    for pr in problemas:
        print(f"CSV invalido: {pr}", file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(principal())
