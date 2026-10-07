"""Fixtures montadas a partir dos próprios schemas."""
import pandas as pd
import pytest


@pytest.fixture
def linha_metricas() -> dict:
    """Uma linha coerente de metricas.csv, usada como base nos testes."""
    return {
        "repo": "owner/nome",
        "freq_release": 1.0,
        "freq_release_pre": 1.2,
        "freq_tag": 1.5,
        "freq_deploy": 0.0,
        "lt_release_h": 312.0,
        "lt_commit_h": 120.0,
        "lt_commit_sem_bots_h": 118.0,
        "pct_commits_bot": 0.1,
        "cfr_a": 0.2,
        "cfr_a_bruto": 0.25,
        "cfr_a_sem_flaky": 0.15,
        "cfr_b": 0.2,
        "cfr_c": 0.1,
        "recuperacao_h": 1.33,
        "recuperacao_sem_flaky_h": 1.1,
        "pct_censurados": 0.05,
        "recuperacao_releases_h": 48.0,
        "rework_rate": 0.4,
        "rework_rate_7d": 0.2,
        "nota_freq": 3,
        "nota_lead_time": 3,
        "nota_cfr": 3,
        "nota_recuperacao": 1,
        "classe_dora": "High",
        "classe_dora_nota": 3,
    }


@pytest.fixture
def df_metricas(linha_metricas) -> pd.DataFrame:
    return pd.DataFrame([linha_metricas])
