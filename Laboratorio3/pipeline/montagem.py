"""Monta metricas.csv e metricas_mensais.csv a partir dos CSVs intermediários."""
from __future__ import annotations

import math
from datetime import date
from typing import Sequence

import pandas as pd

from metricas.cfr import cfr_ci, cfr_issues, pct_falhas_flaky
from metricas.classificacao import classificar_metrica, classificar_repo
from metricas.estaveis import visao_estavel
from metricas.corretiva import cfr_releases, recuperacao_releases, rework_rate
from metricas.frequencia import frequencia
from metricas.lead_time import lead_time_por_commit, lead_time_por_release, pct_commits_bot
from metricas.mensais import series_mensais
from metricas.recuperacao import episodios, mediana_horas, pct_censurados, recuperacao_sem_flaky
from metricas.schemas import SCHEMAS, df_vazio
from pipeline.config import Config


def montar_metricas(
    repos: Sequence[str],
    releases_df: pd.DataFrame,
    commits_df: pd.DataFrame,
    tags_df: pd.DataFrame,
    deployments_df: pd.DataFrame,
    cfg: Config,
    issues_df: "pd.DataFrame | None" = None,
    runs_df: "pd.DataFrame | None" = None,
    attempts_df: "pd.DataFrame | None" = None,
) -> pd.DataFrame:
    """Computa as colunas de metricas.csv: [B], CFR (c), CI e a classe DORA.

    Repositório sem runs fica com as colunas de CI em NaN (não 0): sem dados
    não houve falha nem recuperação. Enquanto cfr_a ou recuperacao_h forem
    NaN, a classe_dora sai da mediana das notas que existem.
    """
    linhas: list[dict] = []

    for repo in repos:
        rel = releases_df[releases_df["repo"] == repo] if not releases_df.empty else pd.DataFrame()
        com = commits_df[commits_df["repo"] == repo] if not commits_df.empty else pd.DataFrame()
        tag = tags_df[tags_df["repo"] == repo] if not tags_df.empty else pd.DataFrame()
        dep = deployments_df[deployments_df["repo"] == repo] if not deployments_df.empty else pd.DataFrame()

        rel_janela = rel[rel["na_janela"]] if not rel.empty and "na_janela" in rel.columns else rel
        dep_suc = dep[dep["estado_final"] == "success"] if not dep.empty and "estado_final" in dep.columns else dep

        # Definição principal de deploy (seção 3 do enunciado): release publicada,
        # sem pré-release. As pré-releases só entram na variante freq_release_pre.
        rel_estavel = (rel_janela[~rel_janela["prerelease"].astype(bool)]
                       if not rel_janela.empty and "prerelease" in rel_janela.columns
                       else rel_janela)

        freq_rel = frequencia(rel_estavel, cfg.janela_inicio, cfg.janela_fim) if not rel_estavel.empty else 0.0
        freq_rel_pre = frequencia(rel, cfg.janela_inicio, cfg.janela_fim) if not rel.empty else 0.0
        freq_tag_ = (frequencia(tag, cfg.janela_inicio, cfg.janela_fim, coluna_data="data_commit")
                     if not tag.empty else 0.0)
        freq_dep_ = (frequencia(dep_suc, cfg.janela_inicio, cfg.janela_fim, coluna_data="criado_em")
                     if not dep_suc.empty else 0.0)

        # Métricas principais (lead time, CFR, recuperação por release, rework):
        # só releases estáveis, com os commits das pré-releases na estável que
        # os entrega. Veja metricas/estaveis.py.
        rel_e, com_e = visao_estavel(rel, com)

        lt_serie = lead_time_por_release(rel_e, com_e) if not rel_e.empty else pd.Series(dtype=float)
        lt_rel = float(lt_serie.median()) if not lt_serie.empty else float("nan")

        lt_com = lead_time_por_commit(rel_e, com_e) if not rel_e.empty else float("nan")
        lt_com_sb = lead_time_por_commit(rel_e, com_e, excluir_bots=True) if not rel_e.empty else float("nan")
        pct_bot = pct_commits_bot(com_e) if not com_e.empty else float("nan")

        cfr_b = cfr_releases(rel_e, com_e, cfg.janela_fim) if not rel_e.empty else float("nan")
        rec_h_serie = recuperacao_releases(rel_e, com_e, cfg.janela_fim) if not rel_e.empty else pd.Series(dtype=float)
        rec_h = float(rec_h_serie.median()) if not rec_h_serie.empty else float("nan")
        rr = rework_rate(rel_e, com_e) if not rel_e.empty else float("nan")
        rr_7d = rework_rate(rel_e, com_e, limite_dias=7) if not rel_e.empty else float("nan")

        iss = (issues_df[issues_df["repo"] == repo]
               if issues_df is not None and not issues_df.empty else pd.DataFrame())
        cfr_c = (cfr_issues(rel_e, iss, cfg.n_dias_issue, "janela", cfg.janela_fim)
                 if not iss.empty and not rel_e.empty else float("nan"))

        run = _do_repo(runs_df, repo)
        att = _do_repo(attempts_df, repo)
        nan = float("nan")
        if run.empty:
            cfr_a = cfr_a_bruto = cfr_a_sem_flaky = pct_flaky = nan
            recuperacao_h = recuperacao_sem_flaky_h = pct_cens = nan
        else:
            a = att if not att.empty else None
            eps = episodios(run, a).df
            cfr_a, cfr_a_bruto = cfr_ci(run), cfr_ci(run, a)
            cfr_a_sem_flaky = cfr_ci(run, a, sem_flaky=True)
            pct_flaky = pct_falhas_flaky(run, a)
            recuperacao_h = mediana_horas(eps)
            recuperacao_sem_flaky_h = recuperacao_sem_flaky(run, a)
            pct_cens = pct_censurados(eps)
        nota_freq = classificar_metrica("freq", freq_rel)
        nota_lt = classificar_metrica("lead_time", lt_rel)
        nota_cfr = classificar_metrica("cfr", cfr_a)
        nota_rec = classificar_metrica("recuperacao", recuperacao_h)
        classe, classe_nota = classificar_repo([nota_freq, nota_lt, nota_cfr, nota_rec])

        linhas.append({
            "repo": repo,
            "freq_release": freq_rel,
            "freq_release_pre": freq_rel_pre,
            "freq_tag": freq_tag_,
            "freq_deploy": freq_dep_,
            "lt_release_h": lt_rel,
            "lt_commit_h": lt_com,
            "lt_commit_sem_bots_h": lt_com_sb,
            "pct_commits_bot": pct_bot,
            "cfr_a": cfr_a,
            "cfr_a_bruto": cfr_a_bruto,
            "cfr_a_sem_flaky": cfr_a_sem_flaky,
            "pct_falhas_flaky": pct_flaky,
            "cfr_b": cfr_b,
            "cfr_c": cfr_c,
            "recuperacao_h": recuperacao_h,
            "recuperacao_sem_flaky_h": recuperacao_sem_flaky_h,
            "pct_censurados": pct_cens,
            "recuperacao_releases_h": rec_h,
            "rework_rate": rr,
            "rework_rate_7d": rr_7d,
            "nota_freq": nota_freq,
            "nota_lead_time": nota_lt,
            "nota_cfr": nota_cfr,
            "nota_recuperacao": nota_rec,
            "classe_dora": classe,
            "classe_dora_nota": classe_nota,
        })

    return pd.DataFrame(linhas) if linhas else df_vazio(SCHEMAS["metricas"])


def _do_repo(df: "pd.DataFrame | None", repo: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df[df["repo"] == repo]


def montar_metricas_mensais(
    repos: Sequence[str],
    runs_df: "pd.DataFrame | None",
    cfg: Config,
    attempts_df: "pd.DataFrame | None" = None,
) -> pd.DataFrame:
    """Monta metricas_mensais.csv. Sem runs devolve DataFrame vazio válido."""
    if runs_df is None or runs_df.empty:
        return df_vazio(SCHEMAS["metricas_mensais"])
    runs = runs_df[runs_df["repo"].isin(list(repos))]
    if runs.empty:
        return df_vazio(SCHEMAS["metricas_mensais"])
    return series_mensais(runs, attempts_df, cfg.min_runs_mes)
