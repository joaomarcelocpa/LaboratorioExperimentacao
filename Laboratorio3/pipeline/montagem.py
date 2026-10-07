"""Monta metricas.csv e metricas_mensais.csv a partir dos CSVs intermediários."""
from __future__ import annotations

import math
from datetime import date
from typing import Sequence

import pandas as pd

from metricas.cfr import cfr_issues
from metricas.classificacao import classificar_metrica, classificar_repo
from metricas.corretiva import cfr_releases, recuperacao_releases, rework_rate
from metricas.frequencia import frequencia
from metricas.lead_time import lead_time_por_commit, lead_time_por_release, pct_commits_bot
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
) -> pd.DataFrame:
    """Computa as colunas [B] de metricas.csv, o CFR (c) e a classe DORA.

    As demais colunas [C] seguem NaN até a integração delas. Enquanto
    cfr_a e recuperacao_h forem NaN, a classe_dora sai da mediana das notas
    que existem, e não das quatro da tabela.
    """
    linhas: list[dict] = []

    for repo in repos:
        rel = releases_df[releases_df["repo"] == repo] if not releases_df.empty else pd.DataFrame()
        com = commits_df[commits_df["repo"] == repo] if not commits_df.empty else pd.DataFrame()
        tag = tags_df[tags_df["repo"] == repo] if not tags_df.empty else pd.DataFrame()
        dep = deployments_df[deployments_df["repo"] == repo] if not deployments_df.empty else pd.DataFrame()

        rel_janela = rel[rel["na_janela"]] if not rel.empty and "na_janela" in rel.columns else rel
        dep_suc = dep[dep["estado_final"] == "success"] if not dep.empty and "estado_final" in dep.columns else dep

        freq_rel = frequencia(rel_janela, cfg.janela_inicio, cfg.janela_fim) if not rel_janela.empty else 0.0
        freq_rel_pre = frequencia(rel, cfg.janela_inicio, cfg.janela_fim) if not rel.empty else 0.0
        freq_tag_ = (frequencia(tag, cfg.janela_inicio, cfg.janela_fim, coluna_data="data_commit")
                     if not tag.empty else 0.0)
        freq_dep_ = (frequencia(dep_suc, cfg.janela_inicio, cfg.janela_fim, coluna_data="criado_em")
                     if not dep_suc.empty else 0.0)

        lt_serie = lead_time_por_release(rel, com) if not rel.empty else pd.Series(dtype=float)
        lt_rel = float(lt_serie.median()) if not lt_serie.empty else float("nan")

        lt_com = lead_time_por_commit(rel, com) if not rel.empty else float("nan")
        lt_com_sb = lead_time_por_commit(rel, com, excluir_bots=True) if not rel.empty else float("nan")
        pct_bot = pct_commits_bot(com) if not com.empty else float("nan")

        cfr_b = cfr_releases(rel, com, cfg.janela_fim) if not rel.empty else float("nan")
        rec_h_serie = recuperacao_releases(rel, com, cfg.janela_fim) if not rel.empty else pd.Series(dtype=float)
        rec_h = float(rec_h_serie.median()) if not rec_h_serie.empty else float("nan")
        rr = rework_rate(rel, com) if not rel.empty else float("nan")
        rr_7d = rework_rate(rel, com, limite_dias=7) if not rel.empty else float("nan")

        iss = (issues_df[issues_df["repo"] == repo]
               if issues_df is not None and not issues_df.empty else pd.DataFrame())
        cfr_c = (cfr_issues(rel, iss, cfg.n_dias_issue, "janela", cfg.janela_fim)
                 if not iss.empty and not rel.empty else float("nan"))

        cfr_a = float("nan")
        recuperacao_h = float("nan")
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
            "cfr_a_bruto": float("nan"),
            "cfr_a_sem_flaky": float("nan"),
            "pct_falhas_flaky": float("nan"),
            "cfr_b": cfr_b,
            "cfr_c": cfr_c,
            "recuperacao_h": recuperacao_h,
            "recuperacao_sem_flaky_h": float("nan"),
            "pct_censurados": float("nan"),
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


def montar_metricas_mensais(
    repos: Sequence[str],
    runs_df: "pd.DataFrame | None",
    cfg: Config,
) -> pd.DataFrame:
    """Monta metricas_mensais.csv. Sem runs_df retorna DataFrame vazio válido."""
    if runs_df is None or runs_df.empty:
        return df_vazio(SCHEMAS["metricas_mensais"])
    return df_vazio(SCHEMAS["metricas_mensais"])
