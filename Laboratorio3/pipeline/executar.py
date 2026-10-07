"""Orquestra seleção → filtros → coleta → métricas e grava os CSVs do contrato.

Toda chamada à API passa por coleta.http (cache, rate limit, custo). As etapas
são injetáveis para que os testes rodem sem rede.
"""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from coleta import http
from metricas.recuperacao import episodios
from metricas.schemas import SCHEMAS, df_vazio, validar
from pipeline.config import Config
from pipeline.montagem import montar_metricas, montar_metricas_mensais

# arquivo gravado por executar() -> chave em SCHEMAS
ARQUIVOS = {
    "repos.csv": "repos",
    "releases.csv": "releases",
    "tags.csv": "tags",
    "commits.csv": "commits",
    "releases_ignoradas.csv": "releases_ignoradas",
    "deployments.csv": "deployments",
    "runs.csv": "runs",
    "run_attempts.csv": "run_attempts",
    "episodios.csv": "episodios",
    "issues_bug.csv": "issues_bug",
    "metricas.csv": "metricas",
    "metricas_mensais.csv": "metricas_mensais",
    "custo_api.csv": "custo_api",
}


def etapas_reais() -> SimpleNamespace:
    from coleta import commits, deployments, issues, metadados, releases, runs, selecao
    from coleta.sessao import SessaoHttp

    return SimpleNamespace(
        selecionar=selecao.selecionar,
        coletar_releases=releases.coletar_releases,
        coletar_commits=commits.coletar_commits,
        coletar_deployments=deployments.coletar_deployments,
        coletar_repos=metadados.coletar_repos,
        coletar_runs=runs.coletar_runs,
        coletar_tentativas=runs.coletar_tentativas,
        coletar_issues_bug=issues.coletar_issues_bug,
        session=SessaoHttp(),
    )


def _juntar(dfs: list[pd.DataFrame], schema: str) -> pd.DataFrame:
    validos = [d for d in dfs if not d.empty]
    return pd.concat(validos, ignore_index=True) if validos else df_vazio(SCHEMAS[schema])


def _gravar(df: pd.DataFrame, nome: str, pasta: Path) -> None:
    validar(df, SCHEMAS[ARQUIVOS[nome]], estrito=False)
    df.to_csv(pasta / nome, index=False)


def executar(
    cfg: Config,
    limite: int | None = None,
    pasta: str | Path = "data/processed",
    etapas: SimpleNamespace | None = None,
) -> dict:
    """Roda o pipeline inteiro. Devolve {"repos": [...], "falhas": {repo: msg}}.

    `limite` vira n_repos antes da seleção, de modo que o sorteio e o funil.csv
    já refletem o limite (cortar a lista depois deixaria o funil inconsistente).
    Um repositório que falha é registrado e os outros seguem; o custo da API é
    gravado mesmo se o processo for interrompido.
    """
    if limite is not None:
        cfg = replace(cfg, n_repos=limite)
    etapas = etapas or etapas_reais()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    falhas: dict[str, str] = {}
    inicio = time.monotonic()

    try:
        amostra = etapas.selecionar(cfg, pasta)
        alvo = amostra["repo"].tolist()
        print(f"selecionados: {len(alvo)} repositórios", flush=True)

        rels, tags, coms, ignoradas, deps = [], [], [], [], []
        coletados: list[str] = []
        for i, repo in enumerate(alvo, 1):
            print(f"  [{i}/{len(alvo)}] {repo}...", end=" ", flush=True)
            try:
                rel, tag = etapas.coletar_releases(repo, cfg, etapas.session)
                com, ign = etapas.coletar_commits(repo, rel, cfg, etapas.session)
                dep = etapas.coletar_deployments(repo, cfg, etapas.session)
            except Exception as exc:  # noqa: BLE001 — um repo ruim não derruba a rodada
                falhas[repo] = f"{type(exc).__name__}: {exc}"
                print(f"erro: {exc}", flush=True)
                continue
            rels.append(rel); tags.append(tag); coms.append(com)
            ignoradas.append(ign); deps.append(dep); coletados.append(repo)
            print("ok", flush=True)

        releases_df, tags_df = _juntar(rels, "releases"), _juntar(tags, "tags")
        commits_df, deployments_df = _juntar(coms, "commits"), _juntar(deps, "deployments")

        repos_df = etapas.coletar_repos(coletados, cfg, commits_df)
        for repo in set(coletados) - set(repos_df["repo"]):
            falhas[repo] = "sem metadados (veja o log de coletar_repos)"
        repos = repos_df["repo"].tolist()

        runs_l, att_l, iss_l, saturadas = [], [], [], []
        for _, linha in repos_df.iterrows():
            repo = linha["repo"]
            try:
                coleta = etapas.coletar_runs(
                    repo, linha["default_branch"], cfg.janela_inicio, cfg.janela_fim)
                tentativas = etapas.coletar_tentativas(
                    repo, coleta.runs, cfg.max_tentativas_anteriores)
                tags_do_repo = tags_df.loc[tags_df["repo"] == repo, "tag"].tolist()
                issues = etapas.coletar_issues_bug(
                    repo, cfg.labels_bug, cfg.janela_inicio, tags_do_repo)
            except Exception as exc:  # noqa: BLE001
                falhas[repo] = f"{type(exc).__name__}: {exc}"
                print(f"  {repo}: erro em runs/issues: {exc}", flush=True)
                continue
            runs_l.append(pd.DataFrame(coleta.runs, columns=list(SCHEMAS["runs"].colunas)))
            att_l.append(pd.DataFrame(tentativas, columns=list(SCHEMAS["run_attempts"].colunas)))
            iss_l.append(pd.DataFrame(issues, columns=list(SCHEMAS["issues_bug"].colunas)))
            saturadas.extend(coleta.saturadas)

        runs_df, att_df = _juntar(runs_l, "runs"), _juntar(att_l, "run_attempts")
        issues_df = _juntar(iss_l, "issues_bug")
        if not issues_df.empty:
            issues_df["cita_tag"] = issues_df["cita_tag"].astype(bool)

        eps_df = (episodios(runs_df, att_df if not att_df.empty else None).df
                  if not runs_df.empty else df_vazio(SCHEMAS["episodios"]))
        metricas_df = montar_metricas(
            repos, releases_df, commits_df, tags_df, deployments_df, cfg,
            issues_df=issues_df, runs_df=runs_df, attempts_df=att_df)
        mensais_df = montar_metricas_mensais(repos, runs_df, cfg, att_df)

        saidas = {
            "repos.csv": repos_df, "releases.csv": releases_df, "tags.csv": tags_df,
            "commits.csv": commits_df, "deployments.csv": deployments_df,
            "releases_ignoradas.csv": _juntar(ignoradas, "releases_ignoradas"),
            "runs.csv": runs_df, "run_attempts.csv": att_df, "episodios.csv": eps_df,
            "issues_bug.csv": issues_df, "metricas.csv": metricas_df,
            "metricas_mensais.csv": mensais_df,
        }
        for nome, df in saidas.items():
            _gravar(df, nome, pasta)
        if saturadas:
            from coleta.runs import escrever_fatias_saturadas
            escrever_fatias_saturadas(saturadas, pasta / "fatias_saturadas.csv")
    finally:
        http.escrever_custo_api(pasta / "custo_api.csv")
        print(f"tempo: {time.monotonic() - inicio:.0f}s | "
              f"custo em {pasta / 'custo_api.csv'}", flush=True)

    if falhas:
        print(f"{len(falhas)} repositório(s) com falha: {', '.join(sorted(falhas))}")
    return {"repos": repos, "falhas": falhas}
