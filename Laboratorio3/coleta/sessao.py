"""Faz o coletor de [B], escrito contra requests.Session, passar pelo cache.

Os coletores de releases, commits e deployments recebem um `session` e
chamam `session.get(url)`. Este adaptador devolve uma resposta com a mesma
interface, mas a chamada vai por coleta.http: cache, rate limit e custo.
"""
from __future__ import annotations

from requests import HTTPError
from requests.structures import CaseInsensitiveDict

from coleta import http


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
    def get(self, url: str, params: dict | None = None, **_) -> RespostaCompat:
        return RespostaCompat(http.get(url, params))
