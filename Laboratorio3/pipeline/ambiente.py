"""Leitura do .env, sem dependência nova.

O cliente HTTP lê GITHUB_TOKEN de os.environ; este módulo é o que faz o token
guardado em .env chegar lá. O que já está no ambiente vence o arquivo, para que
`GITHUB_TOKEN=outro python -m pipeline` continue funcionando. Valores nunca
são impressos.
"""
from __future__ import annotations

import os
from pathlib import Path


def carregar_env(caminho: str | Path = ".env") -> bool:
    """Carrega CHAVE=valor do arquivo para os.environ. Devolve se o arquivo existia."""
    caminho = Path(caminho)
    if not caminho.is_file():
        return False

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip().removeprefix("export ").strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if chave and valor and chave not in os.environ:
            os.environ[chave] = valor
    return True
