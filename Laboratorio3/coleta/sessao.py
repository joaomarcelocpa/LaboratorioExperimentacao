"""Faz o coletor de [B], escrito contra requests.Session, passar pelo cache.

Os coletores de releases, commits e deployments recebem um `session` e
chamam `session.get(url)`. Este adaptador devolve uma resposta com a mesma
interface, mas a chamada vai por coleta.http: cache, rate limit e custo.
"""
from __future__ import annotations

from requests import HTTPError
from requests.structures import CaseInsensitiveDict

import re

from coleta import http

# Mesmo tamanho de página que http.paginar usa: a chave do cache é a mesma,
# então a listagem que o filtro já baixou não é baixada de novo (e a 30 por
# página). /compare fica de fora: o coletor monta ?page=N sem per_page.
_LISTAGENS = re.compile(r"/repos/[^/]+/[^/]+/(releases|tags)$")


class RespostaCompat:
    def __init__(self, r: http.Resposta) -> None:
        self._r = r
        self.status_code = r.status
        self.headers = CaseInsensitiveDict(r.cabecalhos)
        self.text = r.corpo

    def json(self):
        return self._r.json()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPError(f"{self.status_code} para a URL", response=self)


class SessaoHttp:
    def deployments_com_estado(self, repo: str, ambientes: list[str]) -> list[dict] | None:
        """Deployments dos ambientes com o estado final via GraphQL (100 por
        chamada), ou None se o repositório não for achado e o coletor precisar
        do caminho REST."""
        from coleta.deployments_graphql import deployments_com_estado
        return deployments_com_estado(repo, ambientes)

    def tags_com_data(self, repo: str) -> list[dict] | None:
        """Tags com data de commit via GraphQL (100 por chamada), ou None se o
        repositório não for achado e o coletor precisar do caminho REST."""
        from coleta.tags import tags_com_data
        return tags_com_data(repo)

    def get(self, url: str, params: dict | None = None, **_) -> RespostaCompat:
        if params is None and _LISTAGENS.search(url):
            params = {"per_page": http.PER_PAGE_PADRAO}
        return RespostaCompat(http.get(url, params))
