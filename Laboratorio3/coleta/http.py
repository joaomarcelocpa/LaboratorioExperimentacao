"""A única porta de saída para a API do GitHub.

Todo coletor passa por aqui, de modo que cache, retomada, rate limit e
backoff são resolvidos uma vez só. As quatro responsabilidades ficam juntas
de propósito, porque interagem: servir do cache não pode consumir cota, e um
retry conta como chamada.

O enunciado proíbe bibliotecas prontas de acesso à API — só requests.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import pandas as pd
import requests

from coleta.cache import Cache, chave_de
from metricas.schemas import SCHEMAS, validar

TEMPO_LIMITE_S = 30
ESPERAS_5XX = (1, 2, 4, 8, 16)   # 5 esperas, 6 tentativas no total
LIMIAR_COTA = 50                 # abaixo disto, dorme até o Reset
MAX_ESPERAS_COTA = 5             # teto de esperas por rate limit, separado do backoff
TETO_ESPERA_S = 3700             # a cota primária renova em até 1 h
ESPERA_PADRAO_S = 60.0           # rate limit sem nenhum cabeçalho útil
PER_PAGE_PADRAO = 100            # o padrão da API é 30; 100 corta as chamadas em três

# Endpoints paginados que devolvem um objeto em vez de uma lista.
CHAVES_DE_ITENS = (
    "items", "workflow_runs", "commits", "tags", "workflows",
    "check_runs", "artifacts",
)

# O GitHub sempre emite `; rel="..."` logo depois da URL, então não vale
# afrouxar isto para o RFC 8288 inteiro (rel sem aspas, outros parâmetros
# antes do rel) enquanto nenhuma resposta real precisar.
_RE_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="([^"]+)"')

CAMINHO_CUSTO = "data/processed/custo_api.csv"

# Segmentos que identificam um recurso e vêm logo depois de uma coleção.
_DONOS = {
    "repos": ("{owner}", "{repo}"),
    "orgs": ("{org}",),
    "users": ("{user}",),
    "tags": ("{tag}",),
}
_RE_SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)


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

    def cabecalho(self, nome: str) -> str | None:
        """Lê um cabeçalho sem depender de maiúsculas.

        A resposta viva traz o casing do servidor e a cacheada traz um dict
        comum, então o chamador não pode indexar direto.
        """
        return _minusculas(self.cabecalhos).get(nome.lower())

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
    """Converte um cabeçalho em número, ou devolve None se não der.

    float() aceita "inf" e "nan": o primeiro estoura OverflowError no int()
    e o segundo faz time.sleep levantar ValueError. Nenhum dos dois pode
    derrubar uma coleta de 100 repositórios por causa de um cabeçalho torto.
    """
    try:
        n = float(valor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def _recurso_de(url: str) -> str:
    """Qual balde de cota esta URL consome.

    O GitHub conta /search/* num balde próprio. Só usamos esses dois.
    """
    return "search" if urlsplit(url).path.startswith("/search/") else "core"


def _limiar(limite: float | None) -> int:
    """Quantas chamadas guardar de reserva antes de dormir.

    A Issue pede 50, que serve ao balde core (5.000 por hora). O balde de
    busca é de 30 por minuto: ali um limiar de 50 faria o cliente dormir
    depois de toda busca, e a seleção de repositórios faz centenas delas.
    Por isso o limiar encolhe junto com o balde.
    """
    if limite is None or limite <= 0:
        return LIMIAR_COTA
    return max(1, min(LIMIAR_COTA, int(limite // 10)))


def links(cabecalhos: dict) -> dict[str, str]:
    """Relações do cabeçalho Link: next, prev, first, last.

    Público porque o rel="next" não é o único que o estudo usa: a contagem
    de contribuidores (repos.csv) sai do número da última página do
    rel="last", com o truque do per_page=1. Sem isto, cada coletor
    reescreveria este parser.

    Devolve vazio quando não há cabeçalho Link — o caso do repositório com
    um contribuidor só.
    """
    valor = _minusculas(cabecalhos).get("link") or ""
    return {rel: url for url, rel in _RE_LINK.findall(valor)}


def _proximo(cabecalhos: dict) -> str | None:
    """Só rel="next": seguir o rel="last" ou o rel="prev" faria a paginação
    andar para trás."""
    return links(cabecalhos).get("next")


def _itens(carga: Any) -> list[dict]:
    if isinstance(carga, list):
        return carga
    if isinstance(carga, dict):
        for chave in CHAVES_DE_ITENS:
            if isinstance(carga.get(chave), list):
                return carga[chave]
        raise ErroDeHTTP(
            "resposta paginada sem lista de itens reconhecível; chaves "
            f"recebidas: {sorted(carga)}. Acrescente a chave certa a "
            "CHAVES_DE_ITENS em coleta/http.py."
        )
    raise ErroDeHTTP(f"resposta paginada inesperada: {type(carga).__name__}")


def _com_per_page(params: dict | None) -> dict:
    completos = dict(params or {})
    completos.setdefault("per_page", PER_PAGE_PADRAO)
    return completos


def endpoint_de(url: str) -> str:
    """Caminho da URL como template, para agrupar o custo.

    Sem isto, custo_api.csv teria uma linha por repositório em vez de uma por
    endpoint, e não daria para ver onde a cota foi gasta.
    """
    partes = [p for p in urlsplit(url).path.split("/") if p]
    saida: list[str] = []
    i = 0
    while i < len(partes):
        saida.append(partes[i])
        marcadores = _DONOS.get(partes[i], ())
        i += 1
        for marcador in marcadores:
            if i < len(partes):
                saida.append(marcador)
                i += 1
    return "/" + "/".join(_segmento(p) for p in saida)


def _segmento(parte: str) -> str:
    # O intervalo do compare vem antes do sha: `aaa...bbb` é um segmento só,
    # e sem isto cada compare viraria uma linha própria em custo_api.csv.
    if "..." in parte:
        return "{base}...{head}"
    if parte.isdigit():
        return "{id}"
    if _RE_SHA.match(parte):
        return "{sha}"
    return parte


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
        # balde de cota -> (restantes, reset, limiar)
        self._cota: dict[str, tuple[int, float, int]] = {}

    # --- custo ----------------------------------------------------------

    def _contar(self, url: str, campo: str) -> None:
        linha = self._custo.setdefault(endpoint_de(url), {"chamadas": 0, "do_cache": 0})
        linha[campo] += 1

    def custo(self) -> pd.DataFrame:
        """Chamadas que saíram da máquina e acertos de cache, por endpoint."""
        linhas = [
            {"endpoint": ep, "chamadas": v["chamadas"], "do_cache": v["do_cache"]}
            for ep, v in sorted(self._custo.items())
        ]
        df = pd.DataFrame(linhas, columns=["endpoint", "chamadas", "do_cache"])
        return df.astype({"chamadas": "int64", "do_cache": "int64"})

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

    def _registrar_cota(self, url: str, cabecalhos: dict) -> None:
        """Guarda (restantes, reset, limiar) por balde de cota.

        O par é gravado junto ou não é gravado: um Remaining de uma resposta
        casado com o Reset de outra produziria uma espera inventada.
        """
        c = _minusculas(cabecalhos)
        restantes = _numero(c.get("x-ratelimit-remaining"))
        reset = _numero(c.get("x-ratelimit-reset"))
        if restantes is None or reset is None:
            return
        recurso = str(c.get("x-ratelimit-resource") or _recurso_de(url))
        self._cota[recurso] = (
            int(restantes),
            reset,
            _limiar(_numero(c.get("x-ratelimit-limit"))),
        )

    def _esperar_cota(self, url: str) -> None:
        cota = self._cota.get(_recurso_de(url))
        if cota is None:
            return
        restantes, reset, limiar = cota
        if restantes >= limiar:
            return
        segundos = reset - self._agora() + 1
        if segundos > 0:
            self._dormir(min(segundos, TETO_ESPERA_S))
        # Já esperamos; a próxima resposta diz como a cota ficou. Sem isto,
        # dormiríamos antes de toda chamada seguinte.
        self._esquecer_cota(url)

    def _esquecer_cota(self, url: str) -> None:
        self._cota.pop(_recurso_de(url), None)

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
            self._esperar_cota(url)
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

            self._registrar_cota(url, r.headers)

            if _e_rate_limit(r.status_code, r.headers, r.text):
                if esperas_cota >= MAX_ESPERAS_COTA:
                    raise ErroDeHTTP(
                        f"GET {url}: rate limit persistente após "
                        f"{esperas_cota} esperas",
                        r.status_code,
                    )
                self._dormir(self._espera_de_rate_limit(r.headers))
                # Já esperamos por conta desta resposta. Sem esquecer, o
                # _esperar_cota da volta do laço dormiria o mesmo tempo outra
                # vez, dobrando toda espera de rate limit.
                self._esquecer_cota(url)
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

    def paginar(self, url: str, params: dict | None = None) -> list[dict]:
        """Segue Link rel="next" até o fim e devolve todos os itens.

        A URL do rel="next" já carrega os parâmetros, então as páginas
        seguintes vão sem params. Cada página é cacheada pela própria URL, o
        que faz a retomada funcionar no meio de uma paginação longa.
        """
        itens: list[dict] = []
        visitadas: set[str] = set()
        atual: str | None = url
        primeira = True

        while atual and atual not in visitadas:
            visitadas.add(atual)
            r = self.get(atual, _com_per_page(params) if primeira else None)
            if r.status == 404:
                raise ErroDeHTTP(f"GET {atual} devolveu 404 ao paginar", 404)
            itens.extend(_itens(r.json()))
            atual = _proximo(r.cabecalhos)
            primeira = False

        return itens


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


def paginar(url: str, params: dict | None = None) -> list[dict]:
    return cliente_padrao().paginar(url, params)


def escrever_custo_api(
    caminho: str | Path = CAMINHO_CUSTO, cliente: Cliente | None = None
) -> Path:
    """Grava custo_api.csv, validado antes de ir para o disco.

    Validar aqui faz o contrato quebrar neste ponto, e não lá na integração
    da #39, quando ninguém se lembra de onde a coluna veio.
    """
    df = (cliente or cliente_padrao()).custo()
    validar(df, SCHEMAS["custo_api"])
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False)
    return caminho
