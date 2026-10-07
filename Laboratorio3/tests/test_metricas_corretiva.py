import math
from datetime import date
import pandas as pd
from metricas.corretiva import (
    parse_semver, eh_corretiva, cfr_releases, recuperacao_releases, rework_rate
)


# --- parse_semver ---

def test_parse_semver_valido():
    assert parse_semver("v2.3.1") == (2, 3, 1)
    assert parse_semver("2.3.1") == (2, 3, 1)
    assert parse_semver("v1.0.0-rc1") == (1, 0, 0)


def test_parse_semver_invalido():
    assert parse_semver("latest") is None
    assert parse_semver("v2024.01") is None
    assert parse_semver("") is None


# --- eh_corretiva ---

def _commits_fix():
    return pd.DataFrame([{"mensagem": "fix: crash ao abrir arquivo", "eh_bot": False}])


def _commits_feature():
    return pd.DataFrame([{"mensagem": "feat: nova funcionalidade", "eh_bot": False}])


def test_patch_com_commit_fix_e_corretiva():
    assert eh_corretiva("v2.3.0", "v2.3.1", _commits_fix()) is True


def test_major_minor_sem_fix_nao_e_corretiva():
    assert eh_corretiva("v2.4.0", "v2.5.0", _commits_feature()) is False


def test_patch_sem_fix_e_corretiva_pois_so_patch_mudou():
    assert eh_corretiva("v2.3.0", "v2.3.1", _commits_feature()) is True


def test_tag_nao_semver_usa_so_commits():
    assert eh_corretiva("latest", "v2.3.1", _commits_fix()) is True
    assert eh_corretiva("latest", "next", _commits_feature()) is False


def test_commit_hotfix_marca_corretiva():
    commits = pd.DataFrame([{"mensagem": "hotfix: segfault", "eh_bot": False}])
    assert eh_corretiva("v1.0.0", "v1.0.1", commits) is True


def test_commit_revert_marca_corretiva():
    commits = pd.DataFrame([{"mensagem": "revert: undo feat XYZ", "eh_bot": False}])
    assert eh_corretiva("v1.0.0", "v1.0.1", commits) is True


# --- cfr_releases e recuperacao_releases ---

def _releases_seq(rows):
    return pd.DataFrame(rows)


def _commits_para(tag, mensagens):
    return pd.DataFrame([{"release_tag": tag, "mensagem": m, "eh_bot": False}
                          for m in mensagens])


def test_v230_falha_com_48h_de_recuperacao():
    releases = _releases_seq([
        {"tag": "v2.2.0", "publicada_em": "2024-04-01T00:00:00Z", "na_janela": False},
        {"tag": "v2.3.0", "publicada_em": "2024-05-10T00:00:00Z", "na_janela": True},
        {"tag": "v2.3.1", "publicada_em": "2024-05-12T00:00:00Z", "na_janela": True},
    ])
    commits = pd.concat([
        _commits_para("v2.3.0", ["feat: algo"]),
        _commits_para("v2.3.1", ["fix: crash"]),
    ])
    janela_fim = date(2024, 12, 31)

    cfr = cfr_releases(releases, commits, janela_fim)
    assert cfr > 0, "v2.3.0 deve ser contada como falha"

    rec = recuperacao_releases(releases, commits, janela_fim)
    assert abs(rec.iloc[0] - 48.0) < 0.1, f"recuperação esperada 48h, obtida {rec.iloc[0]}"


def test_v240_para_v250_nao_e_falha():
    releases = _releases_seq([
        {"tag": "v2.3.1", "publicada_em": "2024-04-01T00:00:00Z", "na_janela": False},
        {"tag": "v2.4.0", "publicada_em": "2024-06-01T00:00:00Z", "na_janela": True},
        {"tag": "v2.5.0", "publicada_em": "2024-06-20T00:00:00Z", "na_janela": True},
    ])
    commits = pd.concat([
        _commits_para("v2.4.0", ["feat: nova api"]),
        _commits_para("v2.5.0", ["feat: outra feature"]),
    ])
    janela_fim = date(2024, 12, 31)
    cfr = cfr_releases(releases, commits, janela_fim)
    assert cfr == 0.0


def test_releases_nos_ultimos_7_dias_sao_censuradas():
    releases = _releases_seq([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": False},
        {"tag": "v1.1.0", "publicada_em": "2024-12-27T00:00:00Z", "na_janela": True},
    ])
    commits = _commits_para("v1.1.0", ["feat: algo"])
    janela_fim = date(2024, 12, 31)
    cfr = cfr_releases(releases, commits, janela_fim)
    assert math.isnan(cfr) or cfr == 0.0


# --- rework_rate ---

def test_rework_rate_40_pct_sem_limite():
    releases = _releases_seq([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.1.0", "publicada_em": "2024-02-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.1.1", "publicada_em": "2024-02-10T00:00:00Z", "na_janela": True},
        {"tag": "v1.2.0", "publicada_em": "2024-04-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.2.1", "publicada_em": "2024-04-15T00:00:00Z", "na_janela": True},
        {"tag": "v1.3.0", "publicada_em": "2024-06-01T00:00:00Z", "na_janela": True},
    ])
    commits = pd.concat([
        _commits_para("v1.0.0", ["feat: init"]),
        _commits_para("v1.1.0", ["feat: algo"]),
        _commits_para("v1.1.1", ["fix: bug"]),
        _commits_para("v1.2.0", ["feat: algo"]),
        _commits_para("v1.2.1", ["fix: outro bug"]),
        _commits_para("v1.3.0", ["feat: mais"]),
    ])
    rr = rework_rate(releases, commits)
    assert abs(rr - 0.4) < 0.01, f"esperado 0.40, obtido {rr}"


def test_rework_rate_7d_20_pct():
    releases = _releases_seq([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.1.0", "publicada_em": "2024-02-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.1.1", "publicada_em": "2024-02-05T00:00:00Z", "na_janela": True},  # 4 dias
        {"tag": "v1.2.0", "publicada_em": "2024-04-01T00:00:00Z", "na_janela": True},
        {"tag": "v1.2.1", "publicada_em": "2024-04-15T00:00:00Z", "na_janela": True},  # 14 dias
        {"tag": "v1.3.0", "publicada_em": "2024-06-01T00:00:00Z", "na_janela": True},
    ])
    commits = pd.concat([
        _commits_para("v1.0.0", ["feat: init"]),
        _commits_para("v1.1.0", ["feat: algo"]),
        _commits_para("v1.1.1", ["fix: bug"]),
        _commits_para("v1.2.0", ["feat: algo"]),
        _commits_para("v1.2.1", ["fix: outro"]),
        _commits_para("v1.3.0", ["feat: mais"]),
    ])
    rr_full = rework_rate(releases, commits)
    rr_7d = rework_rate(releases, commits, limite_dias=7)
    assert abs(rr_full - 0.4) < 0.01
    assert abs(rr_7d - 0.2) < 0.01
