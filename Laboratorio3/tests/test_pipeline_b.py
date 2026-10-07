"""Testa a montagem de metricas.csv e metricas_mensais.csv."""
import math
from datetime import date
import pandas as pd
from metricas.schemas import SCHEMAS, validar, df_vazio
from pipeline.config import Config
from pipeline.montagem import montar_metricas, montar_metricas_mensais


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1),
        janela_fim=date(2024, 12, 31),
        faixas_estrelas=[],
        min_releases=5, min_runs=50, n_repos=10, seed=42,
        ambientes_producao=["production"],
        labels_bug=["bug"],
        n_dias_issue=7,
        bots=["dependabot[bot]"],
        _janela_placeholder=False,
    )


def _mk_releases(repo):
    return pd.DataFrame([
        {"repo": repo, "tag": "v1.0.0",
         "publicada_em": "2024-01-01T00:00:00Z",
         "prerelease": False, "na_janela": True, "body": ""},
        {"repo": repo, "tag": "v1.1.0",
         "publicada_em": "2024-06-01T00:00:00Z",
         "prerelease": False, "na_janela": True, "body": ""},
        {"repo": repo, "tag": "v1.1.1",
         "publicada_em": "2024-06-05T00:00:00Z",
         "prerelease": False, "na_janela": True, "body": ""},
    ])


def _mk_commits(repo):
    return pd.DataFrame([
        {"repo": repo, "release_tag": "v1.1.0",
         "sha": "abc", "data_autor": "2024-05-01T00:00:00Z",
         "autor_login": "dev", "eh_bot": False, "mensagem": "feat: algo"},
        {"repo": repo, "release_tag": "v1.1.1",
         "sha": "def", "data_autor": "2024-06-04T00:00:00Z",
         "autor_login": "dev", "eh_bot": False, "mensagem": "fix: bug"},
    ])


def _mk_tags(repo):
    return df_vazio(SCHEMAS["tags"]).assign(repo=repo)


def _mk_deployments(repo):
    return df_vazio(SCHEMAS["deployments"]).assign(repo=repo)


def test_montar_metricas_tem_colunas_b():
    cfg = _cfg()
    repo = "org/repo"
    df = montar_metricas(
        [repo],
        _mk_releases(repo),
        _mk_commits(repo),
        _mk_tags(repo),
        _mk_deployments(repo),
        cfg,
    )

    assert len(df) == 1
    row = df.iloc[0]
    assert not math.isnan(row["freq_release"])
    assert not math.isnan(row["lt_release_h"])
    assert not math.isnan(row["cfr_b"])
    assert math.isnan(row["cfr_a"])


def test_montar_metricas_valida_contra_schema():
    cfg = _cfg()
    repo = "org/repo"
    df = montar_metricas(
        [repo],
        _mk_releases(repo),
        _mk_commits(repo),
        _mk_tags(repo),
        _mk_deployments(repo),
        cfg,
    )
    validar(df, SCHEMAS["metricas"], estrito=False)


def test_montar_metricas_mensais_sem_runs_retorna_vazio():
    cfg = _cfg()
    df = montar_metricas_mensais(["org/repo"], runs_df=None, cfg=cfg)
    assert df.empty or list(df.columns) == list(SCHEMAS["metricas_mensais"].colunas)
    validar(df, SCHEMAS["metricas_mensais"])
