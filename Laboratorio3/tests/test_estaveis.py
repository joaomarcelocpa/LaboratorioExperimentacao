"""Visão só de releases estáveis: pré-releases saem, seus commits migram."""
import math
from datetime import date

import pandas as pd
import pytest

from metricas.estaveis import visao_estavel
from metricas.corretiva import cfr_releases
from metricas.lead_time import lead_time_por_release
from pipeline.config import Config
from pipeline.montagem import montar_metricas


def _rel(tag, quando, pre=False, na_janela=True):
    return {"repo": "o/r", "tag": tag, "publicada_em": quando,
            "prerelease": pre, "na_janela": na_janela, "body": ""}


def _com(sha, tag, quando, msg="feat: x"):
    return {"repo": "o/r", "release_tag": tag, "sha": sha, "data_autor": quando,
            "autor_login": "dev", "eh_bot": False, "mensagem": msg}


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1), janela_fim=date(2024, 12, 31),
        faixas_estrelas=[], min_releases=5, min_runs=50, n_repos=10, seed=1,
        ambientes_producao=[], labels_bug=["bug"], n_dias_issue=7, bots=[],
        _janela_placeholder=False,
    )


RELEASES = pd.DataFrame([
    _rel("v1.0.0", "2024-01-10T00:00:00Z"),
    _rel("v1.1.0-rc1", "2024-04-01T00:00:00Z", pre=True),
    _rel("v1.1.0-rc2", "2024-05-01T00:00:00Z", pre=True),
    _rel("v1.1.0", "2024-06-01T00:00:00Z"),
])
COMMITS = pd.DataFrame([
    _com("a", "v1.1.0-rc1", "2024-03-20T00:00:00Z"),
    _com("b", "v1.1.0-rc2", "2024-04-20T00:00:00Z"),
    _com("c", "v1.1.0", "2024-05-25T00:00:00Z"),
])


def test_pre_releases_saem_da_lista():
    rel, _ = visao_estavel(RELEASES, COMMITS)
    assert rel["tag"].tolist() == ["v1.0.0", "v1.1.0"]


def test_commits_da_pre_release_vao_para_a_proxima_estavel():
    _, com = visao_estavel(RELEASES, COMMITS)
    assert set(com["release_tag"]) == {"v1.1.0"}
    assert sorted(com["sha"]) == ["a", "b", "c"]


def test_lead_time_conta_desde_o_commit_mais_antigo_da_pre_release():
    rel, com = visao_estavel(RELEASES, COMMITS)
    horas = lead_time_por_release(rel, com)["v1.1.0"]
    # de 2024-03-20 a 2024-06-01 = 73 dias; sem a visão seriam só 7 dias (c).
    assert horas == pytest.approx(73 * 24)
    bruto = lead_time_por_release(RELEASES, COMMITS)["v1.1.0"]
    assert bruto == pytest.approx(7 * 24)


def test_commits_de_pre_release_sem_estavel_depois_ficam_de_fora():
    rel = pd.DataFrame([_rel("v1.0.0", "2024-01-10T00:00:00Z"),
                        _rel("v2.0.0-rc1", "2024-08-01T00:00:00Z", pre=True)])
    com = pd.DataFrame([_com("a", "v2.0.0-rc1", "2024-07-20T00:00:00Z")])
    _, novos = visao_estavel(rel, com)
    assert novos.empty


def test_sem_pre_releases_nada_muda():
    rel = pd.DataFrame([_rel("v1.0.0", "2024-01-10T00:00:00Z"),
                        _rel("v1.1.0", "2024-06-01T00:00:00Z")])
    com = pd.DataFrame([_com("a", "v1.1.0", "2024-05-25T00:00:00Z")])
    r, c = visao_estavel(rel, com)
    assert r["tag"].tolist() == ["v1.0.0", "v1.1.0"]
    assert c["release_tag"].tolist() == ["v1.1.0"]


def test_vazios_e_sem_coluna_prerelease():
    vazio = pd.DataFrame()
    assert visao_estavel(vazio, vazio)[0].empty
    sem_coluna = RELEASES.drop(columns=["prerelease"])
    assert visao_estavel(sem_coluna, COMMITS)[0].equals(sem_coluna)


def test_so_pre_releases_da_lista_vazia():
    rel = pd.DataFrame([_rel("v1.0.0-rc1", "2024-01-10T00:00:00Z", pre=True)])
    r, c = visao_estavel(rel, pd.DataFrame([_com("a", "v1.0.0-rc1", "2024-01-01T00:00:00Z")]))
    assert r.empty and c.empty


def test_pre_release_de_patch_nao_conta_como_release_corretiva():
    # v1.0.0 -> v1.0.1-rc1 (patch, 2 dias depois): na cadeia completa, v1.0.0
    # "falhou". Na visão estável, não houve release seguinte em 7 dias.
    rel = pd.DataFrame([
        _rel("v0.9.0", "2024-01-05T00:00:00Z"),   # a primeira nunca é avaliada
        _rel("v1.0.0", "2024-02-01T00:00:00Z"),
        _rel("v1.0.1-rc1", "2024-02-03T00:00:00Z", pre=True),
        _rel("v1.1.0", "2024-04-01T00:00:00Z"),
    ])
    com = pd.DataFrame([_com("a", "v1.0.1-rc1", "2024-02-02T00:00:00Z", "fix: crash"),
                        _com("b", "v1.1.0", "2024-03-30T00:00:00Z")])
    fim = date(2024, 12, 31)
    bruto = cfr_releases(rel, com, fim)
    r, c = visao_estavel(rel, com)
    estavel = cfr_releases(r, c, fim)
    assert bruto == pytest.approx(1 / 3)   # v1.0.0 "falhou" por causa do rc
    assert estavel == 0.0


# --- na montagem de metricas.csv ---------------------------------------------

def test_montagem_usa_a_visao_estavel_nas_metricas_principais():
    vazio = pd.DataFrame()
    df = montar_metricas(["o/r"], RELEASES, COMMITS, vazio, vazio, _cfg())
    row = df.iloc[0]
    assert row["lt_release_h"] == pytest.approx(73 * 24)
    # a frequência principal também ignora as pré-releases; a variante conta
    assert row["freq_release_pre"] > row["freq_release"]


def test_montagem_sem_commits_nao_quebra():
    vazio = pd.DataFrame()
    df = montar_metricas(["o/r"], RELEASES, vazio, vazio, vazio, _cfg())
    assert math.isnan(df.iloc[0]["lt_release_h"])
