"""Orquestrador do pipeline.

As cinco etapas são das Issues #38, #39 e #40. Esta Issue (#37) entrega só
a configuração e os contratos de dados.

Uso: python -m pipeline --config config.yaml
"""
from __future__ import annotations

import argparse
import sys

from pipeline.config import ErroDeConfig, carregar_config

ETAPAS = ["selecao", "filtros", "coletores", "normalizacao", "metricas"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    try:
        cfg = carregar_config(args.config)
    except ErroDeConfig as e:
        print(f"erro de configuração: {e}", file=sys.stderr)
        return 2

    if cfg.janela_e_placeholder():
        print(
            "erro: a janela de observação ainda é placeholder. "
            "Preencha janela.inicio/fim no config.yaml com as datas do "
            "professor e remova 'placeholder: true'.",
            file=sys.stderr,
        )
        return 2

    print(f"janela: {cfg.janela_inicio} a {cfg.janela_fim} | n_repos={cfg.n_repos}")
    for etapa in ETAPAS:
        # TODO(#38, #39, #40): implementar as etapas de coleta.
        print(f"  {etapa}: não implementada (Issues #38, #39, #40)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
