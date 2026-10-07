"""Cache em disco das respostas da API do GitHub.

Persistência pura: recebe uma chave e devolve status, cabeçalhos e corpo.
Não sabe que existe HTTP — é o que permite testá-lo sem rede e testar o
cliente sem disco.

A chave é método + URL + parâmetros, e o token fica deliberadamente de fora:
uma resposta guardada com o token de um integrante serve para os outros.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CAMINHO_PADRAO = "data/raw/cache.sqlite"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS respostas (
  chave      TEXT PRIMARY KEY,
  metodo     TEXT NOT NULL,
  url        TEXT NOT NULL,
  params     TEXT NOT NULL,
  status     INTEGER NOT NULL,
  cabecalhos TEXT NOT NULL,
  corpo      TEXT NOT NULL,
  gravado_em TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class RespostaCacheada:
    status: int
    cabecalhos: dict[str, str]
    corpo: str


def _params_canonicos(params: dict | None) -> str:
    """Forma única de um conjunto de parâmetros.

    Valores viram texto porque per_page=100 e per_page="100" produzem a mesma
    requisição. Parâmetros nulos somem porque requests os omite da query: se
    ficassem aqui, duas chamadas idênticas cairiam em linhas diferentes.
    """
    limpos = {str(k): str(v) for k, v in (params or {}).items() if v is not None}
    return json.dumps(limpos, sort_keys=True, separators=(",", ":"))


def chave_de(metodo: str, url: str, params: dict | None = None) -> str:
    bruto = f"{metodo.upper()}\n{url}\n{_params_canonicos(params)}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, caminho: str | Path = CAMINHO_PADRAO) -> None:
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self.caminho))
        self._con.executescript(_ESQUEMA)
        self._con.commit()

    def ler(self, chave: str) -> RespostaCacheada | None:
        linha = self._con.execute(
            "SELECT status, cabecalhos, corpo FROM respostas WHERE chave = ?",
            (chave,),
        ).fetchone()
        if linha is None:
            return None
        status, cabecalhos, corpo = linha
        return RespostaCacheada(
            status=status, cabecalhos=json.loads(cabecalhos), corpo=corpo
        )

    def gravar(
        self,
        chave: str,
        metodo: str,
        url: str,
        params: dict | None,
        status: int,
        cabecalhos: dict,
        corpo: str,
    ) -> None:
        """Grava e faz commit na hora.

        O commit imediato é o que faz a retomada funcionar: um Ctrl+C no meio
        da coleta preserva tudo que já chegou.
        """
        self._con.execute(
            "INSERT OR REPLACE INTO respostas "
            "(chave, metodo, url, params, status, cabecalhos, corpo, gravado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chave,
                metodo.upper(),
                url,
                _params_canonicos(params),
                int(status),
                json.dumps(dict(cabecalhos)),
                corpo,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._con.commit()

    def fechar(self) -> None:
        self._con.close()
