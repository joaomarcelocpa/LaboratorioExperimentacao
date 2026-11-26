"""Texto dos pedidos enviado ao agente.

O agente recebe SO o que o molde congelado define: as secoes [CONTEXTO] a [SAIDA] e, quando existir, a tabela
"Minimo observavel" (identificadores que o teste usa; fazem parte do comportamento). NAO vao ao agente:
o titulo, o tipo (cabe/tensiona), a ordem, o rastreio criterio-teste, o contrato do stub escrito para quem
escreve testes (P9) e as notas de rodape. Mandar o tipo ou o rastreio contaminaria o experimento.
"""
from __future__ import annotations

import re
from pathlib import Path

from harness.config import Config

_ID = re.compile(r"^P(\d{1,2})$")


class PedidoInexistente(Exception):
    pass


def arquivo(cfg: Config, pedido_id: str) -> Path:
    if not _ID.match(pedido_id):
        raise PedidoInexistente(f"identificador de pedido invalido: {pedido_id}")
    for pasta in cfg.pastas_pedidos():
        p = pasta / f"{pedido_id}.md"
        if p.exists():
            return p
    raise PedidoInexistente(f"{pedido_id}.md nao encontrado em {[str(p) for p in cfg.pastas_pedidos()]}")


def _secoes(texto: str) -> tuple[str, dict[str, str]]:
    """Corpo entre o primeiro e o segundo '---' e as secoes '## ...' depois dele."""
    partes = re.split(r"^---\s*$", texto, flags=re.M)
    if len(partes) < 2:
        raise PedidoInexistente("pedido fora do molde: faltam os separadores '---'")
    corpo = partes[1].strip()
    resto = "\n".join(partes[2:])
    secoes: dict[str, str] = {}
    atual = None
    for linha in resto.splitlines():
        m = re.match(r"^##\s+(.*\S)\s*$", linha)
        if m:
            atual = m.group(1)
            secoes[atual] = ""
        elif atual is not None:
            secoes[atual] += linha + "\n"
    return corpo, secoes


def texto_do_pedido(cfg: Config, pedido_id: str) -> str:
    corpo, secoes = _secoes(arquivo(cfg, pedido_id).read_text(encoding="utf-8"))
    for marca in ("[CONTEXTO]", "[NECESSIDADE]", "[COMPORTAMENTO PARA O USUÁRIO]", "[CRITÉRIOS DE ACEITAÇÃO]", "[SAÍDA]"):
        if marca not in corpo:
            raise PedidoInexistente(f"{pedido_id}: secao {marca} ausente (pedido fora do molde)")
    saida = corpo
    minimo = secoes.get("Mínimo observável")
    if minimo:
        linhas = [l for l in minimo.splitlines() if not l.lstrip().startswith(">")]
        tabela = "\n".join(linhas).strip()
        if tabela:
            saida += "\n\nMínimo observável:\n" + tabela
    return saida.strip() + "\n"


def prompt_do_passo(cfg: Config, modo: str, pedidos: list[str], passo: int) -> str:
    """Incremental: so o pedido do passo (a semente e o proprio workspace).
    Regenerado: pedidos acumulados de 1 ate o passo, num unico prompt, sobre a semente limpa."""
    if not 1 <= passo <= len(pedidos):
        raise ValueError(f"passo {passo} fora de 1..{len(pedidos)}")
    if modo == "incremental":
        return texto_do_pedido(cfg, pedidos[passo - 1])
    if modo == "regenerado":
        if passo == 1:
            return texto_do_pedido(cfg, pedidos[0])
        blocos = [f"PEDIDO {i}\n\n{texto_do_pedido(cfg, p)}" for i, p in enumerate(pedidos[:passo], start=1)]
        return "\n\n".join(blocos)
    raise ValueError(f"modo desconhecido: {modo}")
