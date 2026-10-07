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
ESPERAS_5XX = (1, 2, 4, 8, 16)   # 5 esperas, 6 tentativas no total
LIMIAR_COTA = 50                 # abaixo disto, dorme até o Reset
MAX_ESPERAS_COTA = 5             # teto de esperas por rate limit, separado do backoff
TETO_ESPERA_S = 3700             # a cota primária renova em até 1 h
ESPERA_PADRAO_S = 60.0           # rate limit sem nenhum cabeçalho útil


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


def _minusculas(cabecalhos: dict) -> dict[str, str]:
    """O cache devolve um dict comum, não o CaseInsensitiveDict do requests."""
    return {str(k).lower(): v for k, v in (cabecalhos or {}).items()}


def _e_rate_limit(status: int, cabecalhos: dict, corpo: str) -> bool:
    """Separa o 403 de cota do 403 de permissão.

    Sem essa distinção, um 403 de permissão seria repetido cinco vezes,
    queimando cota e escondendo o erro real.
    """
    if status not in (403, 429):
        return False
    c = _minusculas(cabecalhos)
    if "retry-after" in c:
        return True
    if str(c.get("x-ratelimit-remaining", "")) == "0":
        return True
    return "rate limit" in (corpo or "").lower()


def _numero(valor: object) -> float | None:
    try:
        return float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


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
        self._restantes: int | None = None
        self._reset: float | None = None

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

    def _registrar_cota(self, cabecalhos: dict) -> None:
        c = _minusculas(cabecalhos)
        restantes = _numero(c.get("x-ratelimit-remaining"))
        if restantes is not None:
            self._restantes = int(restantes)
        reset = _numero(c.get("x-ratelimit-reset"))
        if reset is not None:
            self._reset = reset

    def _esperar_cota(self) -> None:
        if self._restantes is None or self._restantes >= LIMIAR_COTA:
            return
        if self._reset is None:
            return
        segundos = self._reset - self._agora() + 1
        if segundos > 0:
            self._dormir(min(segundos, TETO_ESPERA_S))
        # Já esperamos; a próxima resposta diz como a cota ficou. Sem isto,
        # dormiríamos antes de toda chamada seguinte.
        self._restantes = None

    def _espera_de_rate_limit(self, cabecalhos: dict) -> float:
        c = _minusculas(cabecalhos)
        # Retry-After pode vir como data HTTP em vez de segundos; nesse caso
        # _numero devolve None e caímos no Reset.
        segundos = _numero(c.get("retry-after"))
        if segundos is None:
            reset = _numero(c.get("x-ratelimit-reset"))
            segundos = None if reset is None else reset - self._agora() + 1
        if segundos is None:
            return ESPERA_PADRAO_S
        return min(max(segundos, 0.0), TETO_ESPERA_S)

    def _buscar(self, url: str, params: dict | None) -> tuple[int, dict, str]:
        """Vai à rede até conseguir uma resposta aproveitável.

        O rate limit tem contador próprio: um 403 de cota não pode consumir o
        backoff de 5xx, senão cinco esperas de cota matariam a coleta.
        """
        cabecalhos = self._cabecalhos()
        tentativa = 0
        esperas_cota = 0

        while True:
            self._esperar_cota()
            self._contar(url, "chamadas")
            try:
                r = self._sessao.get(
                    url, params=params, headers=cabecalhos, timeout=TEMPO_LIMITE_S
                )
            except requests.RequestException as e:
                if tentativa >= len(ESPERAS_5XX):
                    raise ErroDeHTTP(
                        f"GET {url} falhou na rede após {tentativa + 1} tentativas: {e}"
                    ) from e
                self._dormir(ESPERAS_5XX[tentativa])
                tentativa += 1
                continue

            self._registrar_cota(r.headers)

            if _e_rate_limit(r.status_code, r.headers, r.text):
                if esperas_cota >= MAX_ESPERAS_COTA:
                    raise ErroDeHTTP(
                        f"GET {url}: rate limit persistente após "
                        f"{esperas_cota} esperas",
                        r.status_code,
                    )
                self._dormir(self._espera_de_rate_limit(r.headers))
                # Já esperamos por conta desta resposta. Sem zerar, o
                # _esperar_cota da volta do laço dormiria o mesmo tempo outra
                # vez, dobrando toda espera de rate limit.
                self._restantes = None
                esperas_cota += 1
                continue

            if r.status_code >= 500:
                if tentativa >= len(ESPERAS_5XX):
                    raise ErroDeHTTP(
                        f"GET {url} devolveu {r.status_code} após "
                        f"{tentativa + 1} tentativas",
                        r.status_code,
                    )
                self._dormir(ESPERAS_5XX[tentativa])
                tentativa += 1
                continue

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
