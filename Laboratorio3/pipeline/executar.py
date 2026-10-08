"""Orquestra seleção → filtros → coleta → métricas e grava os CSVs do contrato.

Toda chamada à API passa por coleta.http (cache, rate limit, custo). As etapas
são injetáveis para que os testes rodem sem rede.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace
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
    """Valida e grava de forma atômica: um Ctrl-C no meio da escrita não deixa
    um CSV pela metade no lugar do checkpoint anterior."""
    validar(df, SCHEMAS[ARQUIVOS[nome]], estrito=False)
    tmp = pasta / f"{nome}.tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, pasta / nome)


def _repassa_401(exc: Exception) -> None:
    """Token inválido não é falha de um repo: esconder isso deixaria a rodada
    inteira 'terminar' com CSVs vazios."""
    if isinstance(exc, http.ErroDeHTTP) and exc.status == 401:
        raise exc


@dataclass
class _Completos:
    """Só o que veio de repositórios COMPLETOS (todas as etapas coletadas).

    Um repositório entra aqui de uma vez, depois da última etapa; por isso um
    checkpoint nunca contém um repo pela metade.
    """

    rels: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    coms: list = field(default_factory=list)
    ignoradas: list = field(default_factory=list)
    deps: list = field(default_factory=list)
    repos: list = field(default_factory=list)
    runs: list = field(default_factory=list)
    atts: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    saturadas: list = field(default_factory=list)


def _gravar_saidas(acc: _Completos, cfg: Config, pasta: Path) -> list[str]:
    """Monta as métricas do que está completo e grava todos os CSVs."""
    repos_df = _juntar(acc.repos, "repos")
    repos = repos_df["repo"].tolist()
    releases_df, tags_df = _juntar(acc.rels, "releases"), _juntar(acc.tags, "tags")
    commits_df = _juntar(acc.coms, "commits")
    deployments_df = _juntar(acc.deps, "deployments")
    runs_df, att_df = _juntar(acc.runs, "runs"), _juntar(acc.atts, "run_attempts")
    issues_df = _juntar(acc.issues, "issues_bug")
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
        "releases_ignoradas.csv": _juntar(acc.ignoradas, "releases_ignoradas"),
        "runs.csv": runs_df, "run_attempts.csv": att_df, "episodios.csv": eps_df,
        "issues_bug.csv": issues_df, "metricas.csv": metricas_df,
        "metricas_mensais.csv": mensais_df,
    }
    for nome, df in saidas.items():
        _gravar(df, nome, pasta)
    if acc.saturadas:
        from coleta.runs import escrever_fatias_saturadas
        escrever_fatias_saturadas(acc.saturadas, pasta / "fatias_saturadas.csv")
    return repos


def executar(
    cfg: Config,
    limite: int | None = None,
    pasta: str | Path = "data/processed",
    etapas: SimpleNamespace | None = None,
) -> dict:
    """Roda o pipeline inteiro. Devolve {"repos": [...], "falhas": {repo: msg}}.

    `limite` vira n_repos antes da seleção, de modo que o sorteio e o funil.csv
    já refletem o limite (cortar a lista depois deixaria o funil inconsistente).
    Um repositório que falha é registrado e os outros seguem. Cada repositório é
    coletado por inteiro e os CSVs são regravados (atomicamente) depois de cada
    um, então uma interrupção deixa em disco tudo o que já estava completo; o
    custo da API também é gravado.
    """
    if limite is not None:
        cfg = replace(cfg, n_repos=limite)
    etapas = etapas or etapas_reais()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    falhas: dict[str, str] = {}
    inicio = time.monotonic()
    # Uma rodada anterior pode ter deixado este diagnóstico; lido agora, ele
    # pareceria ameaça à validade desta amostra.
    (pasta / "fatias_saturadas.csv").unlink(missing_ok=True)

    try:
        amostra = etapas.selecionar(cfg, pasta)
        alvo = amostra["repo"].tolist()
        # A seleção custa o mesmo para qualquer tamanho de amostra; guardá-la
        # à parte deixa estimar() separar o custo fixo do custo por repo.
        cliente = http.cliente_padrao()
        cliente.custo().to_csv(pasta / "custo_selecao.csv", index=False)
        print(f"selecionados: {len(alvo)} repositórios "
              f"(seleção: {time.monotonic() - inicio:.0f}s)", flush=True)

        acc = _Completos()
        repos: list[str] = []
        for i, repo in enumerate(alvo, 1):
            print(f"  [{i}/{len(alvo)}] {repo}...", end=" ", flush=True)
            try:
                rel, tag = etapas.coletar_releases(repo, cfg, etapas.session)
                com, ign = etapas.coletar_commits(repo, rel, cfg, etapas.session)
                dep = etapas.coletar_deployments(repo, cfg, etapas.session)
                meta = etapas.coletar_repos([repo], cfg, com)
                if meta.empty:
                    raise LookupError("sem metadados (veja o log de coletar_repos)")
                coleta = etapas.coletar_runs(
                    repo, meta.iloc[0]["default_branch"],
                    cfg.janela_inicio, cfg.janela_fim)
                tentativas = etapas.coletar_tentativas(
                    repo, coleta.runs, cfg.max_tentativas_anteriores)
                issues = etapas.coletar_issues_bug(
                    repo, cfg.labels_bug, cfg.janela_inicio, tag["tag"].tolist())
            except Exception as exc:  # noqa: BLE001 — um repo ruim não derruba a rodada
                _repassa_401(exc)
                falhas[repo] = f"{type(exc).__name__}: {exc}"
                print(f"erro: {exc}", flush=True)
                continue

            acc.rels.append(rel); acc.tags.append(tag); acc.coms.append(com)
            acc.ignoradas.append(ign); acc.deps.append(dep); acc.repos.append(meta)
            acc.runs.append(pd.DataFrame(coleta.runs, columns=list(SCHEMAS["runs"].colunas)))
            acc.atts.append(pd.DataFrame(tentativas, columns=list(SCHEMAS["run_attempts"].colunas)))
            acc.issues.append(pd.DataFrame(issues, columns=list(SCHEMAS["issues_bug"].colunas)))
            acc.saturadas.extend(coleta.saturadas)
            # Checkpoint: se a rodada for interrompida daqui em diante, os
            # repositórios completos já estão nos CSVs.
            repos = _gravar_saidas(acc, cfg, pasta)
            print(f"ok ({len(repos)} completos)", flush=True)

        repos = _gravar_saidas(acc, cfg, pasta)
    finally:
        http.escrever_custo_api(pasta / "custo_api.csv")
        print(f"tempo: {time.monotonic() - inicio:.0f}s | "
              f"custo em {pasta / 'custo_api.csv'}", flush=True)

    if falhas:
        print(f"{len(falhas)} repositório(s) com falha: {', '.join(sorted(falhas))}")
    return {"repos": repos, "falhas": falhas}
