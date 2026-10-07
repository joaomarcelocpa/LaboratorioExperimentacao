import math
import pandas as pd
from metricas.lead_time import lead_time_por_release, lead_time_por_commit, pct_commits_bot


def _releases(rows):
    return pd.DataFrame(rows)


def _commits(rows):
    return pd.DataFrame(rows)


def test_v11_lead_time_por_release_13_dias():
    # v1.1 publicada 15/03; commits em 02/03, 10/03, 14/03
    # lead time = 15/03 - 02/03 = 13 dias = 312h
    releases = _releases([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": False},
        {"tag": "v1.1.0", "publicada_em": "2024-03-15T00:00:00Z", "na_janela": True},
    ])
    commits = _commits([
        {"release_tag": "v1.1.0", "data_autor": "2024-03-02T00:00:00Z", "eh_bot": False},
        {"release_tag": "v1.1.0", "data_autor": "2024-03-10T00:00:00Z", "eh_bot": False},
        {"release_tag": "v1.1.0", "data_autor": "2024-03-14T00:00:00Z", "eh_bot": False},
    ])
    serie = lead_time_por_release(releases, commits)
    lt_h = serie["v1.1.0"]
    assert abs(lt_h - 13 * 24) < 1, f"esperado 312h (13d), obtido {lt_h}"


def test_v11_lead_time_por_commit_mediana():
    # Variante (b): contribui com [13d, 5d, 1d]; mediana = 5d = 120h
    releases = _releases([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": False},
        {"tag": "v1.1.0", "publicada_em": "2024-03-15T00:00:00Z", "na_janela": True},
    ])
    commits = _commits([
        {"release_tag": "v1.1.0", "data_autor": "2024-03-02T00:00:00Z", "eh_bot": False},
        {"release_tag": "v1.1.0", "data_autor": "2024-03-10T00:00:00Z", "eh_bot": False},
        {"release_tag": "v1.1.0", "data_autor": "2024-03-14T00:00:00Z", "eh_bot": False},
    ])
    lt = lead_time_por_commit(releases, commits)
    assert abs(lt - 5 * 24) < 1, f"esperado 120h (5d), obtido {lt}"


def test_release_sem_commits_novos_retorna_nan():
    releases = _releases([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": False},
        {"tag": "v1.1.0", "publicada_em": "2024-03-01T00:00:00Z", "na_janela": True},
    ])
    commits = _commits([])
    serie = lead_time_por_release(releases, commits)
    assert math.isnan(serie.get("v1.1.0", float("nan")))


def test_primeira_release_da_historia_excluida():
    releases = _releases([
        {"tag": "v1.0.0", "publicada_em": "2024-03-01T00:00:00Z", "na_janela": True},
    ])
    commits = _commits([
        {"release_tag": "v1.0.0", "data_autor": "2024-02-01T00:00:00Z", "eh_bot": False},
    ])
    serie = lead_time_por_release(releases, commits)
    assert "v1.0.0" not in serie.index or math.isnan(serie.get("v1.0.0", float("nan")))


def test_excluir_bots_retorna_nan_se_so_bots():
    releases = _releases([
        {"tag": "v1.0.0", "publicada_em": "2024-01-01T00:00:00Z", "na_janela": False},
        {"tag": "v1.1.0", "publicada_em": "2024-03-01T00:00:00Z", "na_janela": True},
    ])
    commits = _commits([
        {"release_tag": "v1.1.0", "data_autor": "2024-02-15T00:00:00Z", "eh_bot": True},
    ])
    lt = lead_time_por_commit(releases, commits, excluir_bots=True)
    assert math.isnan(lt)


def test_pct_commits_bot():
    commits = _commits([
        {"eh_bot": True}, {"eh_bot": False}, {"eh_bot": False}, {"eh_bot": True},
    ])
    assert pct_commits_bot(commits) == 0.5


def test_pct_commits_bot_df_vazio():
    commits = pd.DataFrame({"eh_bot": []})
    assert math.isnan(pct_commits_bot(commits))
