"""Orquestrador do pipeline.

Uso: python -m pipeline --config config.yaml [--limite N]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import requests

from metricas.schemas import SCHEMAS, df_vazio, validar
from pipeline.config import ErroDeConfig, carregar_config
from pipeline.montagem import montar_metricas, montar_metricas_mensais

ETAPAS = ["selecao", "filtros", "coletores", "normalizacao", "metricas"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--limite", type=int, default=None,
        help="Máximo de repositórios a processar (sobrepõe n_repos do config)",
    )
    args = parser.parse_args(argv)

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

    limite = args.limite if args.limite is not None else cfg.n_repos
    print(f"janela: {cfg.janela_inicio} a {cfg.janela_fim} | limite={limite}")

    dados_dir = Path("dados")
    dados_dir.mkdir(exist_ok=True)

    repos_csv = dados_dir / "repos.csv"
    if not repos_csv.exists():
        print(f"  selecao/filtros: aguardando {repos_csv} (responsabilidade [A])")
        return 0

    repos_df = pd.read_csv(repos_csv)
    repos = repos_df["repo"].tolist()[:limite]
    print(f"  {len(repos)} repositórios carregados de {repos_csv}")

    from coleta.commits import coletar_commits
    from coleta.deployments import coletar_deployments
    from coleta.releases import coletar_releases

    session = requests.Session()
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    session.headers["Accept"] = "application/vnd.github+json"
    session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    all_releases: list[pd.DataFrame] = []
    all_commits: list[pd.DataFrame] = []
    all_ignoradas: list[pd.DataFrame] = []
    all_tags: list[pd.DataFrame] = []
    all_deployments: list[pd.DataFrame] = []

    for i, repo in enumerate(repos, 1):
        print(f"  [{i}/{len(repos)}] coletando {repo}...", end=" ", flush=True)
        try:
            rel_df, tag_df = coletar_releases(repo, cfg, session)
            com_df, ign_df = coletar_commits(repo, rel_df, cfg, session)
            dep_df = coletar_deployments(repo, cfg, session)
            all_releases.append(rel_df)
            all_commits.append(com_df)
            all_ignoradas.append(ign_df)
            all_tags.append(tag_df)
            all_deployments.append(dep_df)
            print("ok")
        except Exception as exc:
            print(f"erro: {exc}")

    def _concat(dfs: list[pd.DataFrame], schema_name: str) -> pd.DataFrame:
        validos = [d for d in dfs if not d.empty]
        return pd.concat(validos, ignore_index=True) if validos else df_vazio(SCHEMAS[schema_name])

    releases_df = _concat(all_releases, "releases")
    commits_df = _concat(all_commits, "commits")
    tags_df = _concat(all_tags, "tags")
    deployments_df = _concat(all_deployments, "deployments")
    ignoradas_df = _concat(all_ignoradas, "releases_ignoradas")

    releases_df.to_csv(dados_dir / "releases.csv", index=False)
    commits_df.to_csv(dados_dir / "commits.csv", index=False)
    tags_df.to_csv(dados_dir / "tags.csv", index=False)
    deployments_df.to_csv(dados_dir / "deployments.csv", index=False)
    ignoradas_df.to_csv(dados_dir / "releases_ignoradas.csv", index=False)
    print(f"  CSVs intermediários gravados em {dados_dir}/")

    runs_csv = dados_dir / "runs.csv"
    runs_df = pd.read_csv(runs_csv) if runs_csv.exists() else None

    metricas_df = montar_metricas(repos, releases_df, commits_df, tags_df, deployments_df, cfg)
    metricas_mensais_df = montar_metricas_mensais(repos, runs_df, cfg)

    validar(metricas_df, SCHEMAS["metricas"], estrito=False)
    validar(metricas_mensais_df, SCHEMAS["metricas_mensais"])

    metricas_df.to_csv(dados_dir / "metricas.csv", index=False)
    metricas_mensais_df.to_csv(dados_dir / "metricas_mensais.csv", index=False)
    print(f"  metricas.csv ({len(metricas_df)} repos) e metricas_mensais.csv gravados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
