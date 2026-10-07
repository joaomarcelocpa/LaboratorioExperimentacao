"""A única porta de saída para a API do GitHub.

Todo coletor passa por aqui, de modo que cache, retomada, rate limit e
backoff são resolvidos uma vez só. As quatro responsabilidades ficam juntas
de propósito, porque interagem: servir do cache não pode consumir cota, e um
retry conta como chamada.

O enunciado proíbe bibliotecas prontas de acesso à API — só requests.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from coleta.cache import Cache, chave_de

TEMPO_LIMITE_S = 30


class ErroDeHTTP(Exception):
    """Resposta que o cliente não sabe aproveitar nem vale a pena repetir.

    Carrega o status para que o chamador decida: `if erro.status == 404`.
    """

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


@dataclass(frozen=True)
class Resposta:
    status: int
    cabecalhos: dict[str, str]
    corpo: str
    do_cache: bool

    def json(self) -> Any:
        try:
            return json.loads(self.corpo)
        except json.JSONDecodeError as e:
            raise ErroDeHTTP(
                f"resposta não era JSON (status {self.status}): {self.corpo[:200]}",
                self.status,
            ) from e


def _e_cacheavel(status: int) -> bool:
    """2xx e 404, e nada mais.

    Um 5xx ou um rate limit cacheado envenenaria a coleta para sempre.
    """
    return 200 <= status < 300 or status == 404


class Cliente:
    def __init__(
        self,
        token: str | None = None,
        cache: Cache | None = None,
        sessao: requests.Session | None = None,
        agora: Callable[[], float] = time.time,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self._cache = cache if cache is not None else Cache()
        self._sessao = sessao if sessao is not None else requests.Session()
        self._agora = agora
        self._dormir = dormir
        self._custo: dict[str, dict[str, int]] = {}

    # --- custo ----------------------------------------------------------

    def _contar(self, url: str, campo: str) -> None:
        linha = self._custo.setdefault(url, {"chamadas": 0, "do_cache": 0})
        linha[campo] += 1

    # --- requisição -----------------------------------------------------

    def _cabecalhos(self) -> dict[str, str]:
        if not self._token:
            raise ErroDeHTTP(
                "GITHUB_TOKEN não definido: exporte o token antes de coletar "
                "(veja .env.example). Sem ele, só respostas já em cache funcionam."
            )
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lab03-dora",
        }

    def _buscar(self, url: str, params: dict | None) -> tuple[int, dict, str]:
        """Uma ida à rede."""
        cabecalhos = self._cabecalhos()
        self._contar(url, "chamadas")
        r = self._sessao.get(
            url, params=params, headers=cabecalhos, timeout=TEMPO_LIMITE_S
        )
        return r.status_code, dict(r.headers), r.text

    def get(self, url: str, params: dict | None = None) -> Resposta:
        chave = chave_de("GET", url, params)

        guardada = self._cache.ler(chave)
        if guardada is not None:
            self._contar(url, "do_cache")
            return Resposta(guardada.status, guardada.cabecalhos, guardada.corpo, True)

        status, cabecalhos, corpo = self._buscar(url, params)
        if _e_cacheavel(status):
            self._cache.gravar(chave, "GET", url, params, status, cabecalhos, corpo)
            return Resposta(status, cabecalhos, corpo, False)

        raise ErroDeHTTP(f"GET {url} devolveu {status}: {corpo[:200]}", status)


# --- cliente padrão do processo -----------------------------------------

_CLIENTE: Cliente | None = None


def cliente_padrao() -> Cliente:
    global _CLIENTE
    if _CLIENTE is None:
        _CLIENTE = Cliente()
    return _CLIENTE


def redefinir_cliente(cliente: Cliente | None = None) -> None:
    """Troca o cliente do processo. Usado pelos testes."""
    global _CLIENTE
    _CLIENTE = cliente


def get(url: str, params: dict | None = None) -> Resposta:
    return cliente_padrao().get(url, params)
