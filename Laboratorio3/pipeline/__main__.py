"""Ponto de entrada do pipeline.

Uso: python -m pipeline --config config.yaml [--limite N]
Requer GITHUB_TOKEN no ambiente ou em .env.
"""
from __future__ import annotations

import argparse
import sys

from pipeline.ambiente import carregar_env
from pipeline.config import ErroDeConfig, carregar_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--limite", type=int, default=None,
        help="Quantos repositórios entram na amostra (sobrepõe n_repos do config)",
    )
    args = parser.parse_args(argv)
    carregar_env()

    if args.limite is not None and args.limite < 1:
        print("erro: --limite deve ser um inteiro >= 1", file=sys.stderr)
        return 2

    try:
        cfg = carregar_config(args.config)
    except ErroDeConfig as e:
        print(f"erro de configuração: {e}", file=sys.stderr)
        return 2

    if cfg.janela_e_placeholder():
        print(
            "erro: a janela de observação ainda é placeholder. "
            "Preencha janela.inicio/fim no config.yaml e remova 'placeholder: true'.",
            file=sys.stderr,
        )
        return 2

    from pipeline.executar import executar

    print(f"janela: {cfg.janela_inicio} a {cfg.janela_fim} | "
          f"amostra: {args.limite or cfg.n_repos}")
    resultado = executar(cfg, limite=args.limite)
    if resultado["falhas"] and not resultado["repos"]:
        print("erro: nenhum repositório foi coletado com sucesso", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
