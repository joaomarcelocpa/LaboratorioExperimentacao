"""Leitura e validação do config.yaml.

Falha cedo e com mensagem clara: um erro de configuração descoberto no meio
de uma coleta de 100 repositórios custa horas de cota da API.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


class ErroDeConfig(Exception):
    """Configuração ausente, malformada ou com tipo errado."""


@dataclass(frozen=True)
class Config:
    janela_inicio: date
    janela_fim: date
    faixas_estrelas: list[str]
    min_releases: int
    min_runs: int
    n_repos: int
    seed: int
    ambientes_producao: list[str]
    labels_bug: list[str]
    n_dias_issue: int
    bots: list[str]
    max_tentativas_anteriores: int = 5
    _janela_placeholder: bool = True

    def janela_e_placeholder(self) -> bool:
        """True enquanto a janela do professor não for preenchida."""
        return self._janela_placeholder


# chave -> tipo esperado
_ESCALARES: dict[str, type] = {
    "min_releases": int,
    "min_runs": int,
    "n_repos": int,
    "seed": int,
    "n_dias_issue": int,
}
_LISTAS = ["faixas_estrelas", "ambientes_producao", "labels_bug", "bots"]


def carregar_config(caminho: str | Path = "config.yaml") -> Config:
    caminho = Path(caminho)
    if caminho.is_dir():
        raise ErroDeConfig(f"config é um diretório, não um arquivo: {caminho}")
    if not caminho.is_file():
        raise ErroDeConfig(f"config não encontrado: {caminho}")

    try:
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ErroDeConfig(f"YAML inválido em {caminho}: {e}") from e

    if not isinstance(dados, dict):
        raise ErroDeConfig(
            f"{caminho}: o topo do arquivo precisa ser um mapa de chaves, "
            f"encontrado {type(dados).__name__}"
        )

    janela = dados.get("janela")
    if not isinstance(janela, dict):
        raise ErroDeConfig(f"{caminho}: chave 'janela' ausente ou não é um mapa")
    for campo in ("inicio", "fim"):
        if campo not in janela:
            raise ErroDeConfig(f"{caminho}: chave 'janela.{campo}' ausente")
        # datetime é subclasse de date: sem o type() exato, uma data com hora
        # passaria aqui e estouraria TypeError na comparação abaixo.
        if type(janela[campo]) is not date:
            raise ErroDeConfig(
                f"{caminho}: 'janela.{campo}' deve ser uma data AAAA-MM-DD "
                f"sem hora, encontrado {type(janela[campo]).__module__}."
                f"{type(janela[campo]).__name__}"
            )
    if janela["fim"] < janela["inicio"]:
        raise ErroDeConfig(
            f"{caminho}: 'janela.fim' ({janela['fim']}) é anterior a "
            f"'janela.inicio' ({janela['inicio']})"
        )

    for chave, tipo in _ESCALARES.items():
        if chave not in dados:
            raise ErroDeConfig(f"{caminho}: chave '{chave}' ausente")
        valor = dados[chave]
        # bool é subclasse de int em Python; aqui seria erro.
        if not isinstance(valor, tipo) or isinstance(valor, bool):
            raise ErroDeConfig(
                f"{caminho}: '{chave}' deve ser {tipo.__name__}, "
                f"encontrado {type(valor).__name__}"
            )

    for chave in _LISTAS:
        if chave not in dados:
            raise ErroDeConfig(f"{caminho}: chave '{chave}' ausente")
        if not isinstance(dados[chave], list):
            raise ErroDeConfig(
                f"{caminho}: '{chave}' deve ser list, "
                f"encontrado {type(dados[chave]).__name__}"
            )

    # Opcional: um config.yaml escrito antes desta chave continua válido.
    max_tentativas = dados.get("max_tentativas_anteriores", 5)
    if not isinstance(max_tentativas, int) or isinstance(max_tentativas, bool):
        raise ErroDeConfig(
            f"{caminho}: 'max_tentativas_anteriores' deve ser int, "
            f"encontrado {type(max_tentativas).__name__}"
        )
    if max_tentativas < 1:
        raise ErroDeConfig(
            f"{caminho}: 'max_tentativas_anteriores' deve ser >= 1, "
            f"encontrado {max_tentativas}. Zero desligaria a coleta de "
            f"tentativas sem dizer."
        )

    return Config(
        janela_inicio=janela["inicio"],
        janela_fim=janela["fim"],
        faixas_estrelas=dados["faixas_estrelas"],
        min_releases=dados["min_releases"],
        min_runs=dados["min_runs"],
        n_repos=dados["n_repos"],
        seed=dados["seed"],
        ambientes_producao=dados["ambientes_producao"],
        labels_bug=dados["labels_bug"],
        n_dias_issue=dados["n_dias_issue"],
        bots=dados["bots"],
        max_tentativas_anteriores=max_tentativas,
        _janela_placeholder=bool(janela.get("placeholder", False)),
    )
