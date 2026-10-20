import math
import numpy as np
import pandas as pd
import pytest
from analise.rq05 import correlacao_spearman


def test_correlacao_perfeita_positiva():
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    r = correlacao_spearman(x, y)
    assert r["rho"] == pytest.approx(1.0, abs=1e-9)
    assert r["n"] == 5


def test_correlacao_perfeita_negativa():
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([10.0, 8.0, 6.0, 4.0, 2.0])
    r = correlacao_spearman(x, y)
    assert r["rho"] == pytest.approx(-1.0, abs=1e-9)


def test_correlacao_descarta_nan():
    x = pd.Series([1.0, 2.0, float("nan"), 4.0])
    y = pd.Series([2.0, 4.0, 6.0, 8.0])
    r = correlacao_spearman(x, y)
    assert r["n"] == 3


def test_correlacao_retorna_pvalue():
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    r = correlacao_spearman(x, y)
    assert "pvalue" in r
    assert 0.0 <= r["pvalue"] <= 1.0


def test_correlacao_sem_dados_validos_retorna_nan():
    x = pd.Series([float("nan"), float("nan")])
    y = pd.Series([1.0, 2.0])
    r = correlacao_spearman(x, y)
    assert math.isnan(r["rho"])
    assert r["n"] == 0


# --- tabela_correlacoes ---

from analise.rq05 import tabela_correlacoes


def _df_fake() -> pd.DataFrame:
    return pd.DataFrame({
        "freq_release": [0.1, 0.5, 1.0, 2.0, 5.0],
        "cfr_a":        [0.4, 0.3, 0.2, 0.1, 0.05],
        "cfr_b":        [0.5, 0.4, 0.3, 0.2, 0.1],
    })


def test_tabela_tem_duas_linhas():
    tabela = tabela_correlacoes(_df_fake())
    assert len(tabela) == 2


def test_tabela_tem_colunas_obrigatorias():
    tabela = tabela_correlacoes(_df_fake())
    for col in ("variante", "rho", "pvalue", "n", "significativo"):
        assert col in tabela.columns, f"coluna ausente: {col}"


def test_tabela_variantes_sao_cfr_a_e_cfr_b():
    tabela = tabela_correlacoes(_df_fake())
    assert set(tabela["variante"]) == {"cfr_a", "cfr_b"}


def test_tabela_significativo_e_bool():
    tabela = tabela_correlacoes(_df_fake())
    assert tabela["significativo"].dtype == bool


# --- scatter_freq_cfr ---

from analise.rq05 import scatter_freq_cfr


def test_scatter_cria_arquivo_png(tmp_path):
    df = _df_fake()
    destino = tmp_path / "rq05_scatter_cfr_a.png"
    scatter_freq_cfr(df, "cfr_a", rho=-0.9, pvalue=0.01, caminho_saida=destino)
    assert destino.exists()
    assert destino.stat().st_size > 0


def test_scatter_cria_diretorio_se_nao_existir(tmp_path):
    df = _df_fake()
    destino = tmp_path / "subdir" / "plot.png"
    scatter_freq_cfr(df, "cfr_b", rho=0.5, pvalue=0.05, caminho_saida=destino)
    assert destino.exists()
