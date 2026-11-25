import pandas as pd
import pytest

from analysis import descritiva, figuras, models
from analysis.synthetic import Parametros, gerar


@pytest.fixture(scope="module")
def df():
    # falhas frequentes para exercitar a censura
    return gerar(8, parametros=Parametros(p_falha_execucao=0.3), seed=11)


def test_por_passo_mostra_n_e_censura(df):
    t = descritiva.por_passo(df)
    assert {"cadeias_no_passo", "cadeias_ok", "censuradas_ate_o_passo", "regressao_acumulada"} <= set(t.columns)
    assert set(descritiva.METRICAS) <= set(t.columns)
    for _, g in t.groupby("mode"):
        g = g.sort_values("step")
        assert g["censuradas_ate_o_passo"].is_monotonic_increasing
        assert (g["cadeias_no_passo"].iloc[0] == 8)
    assert t["censuradas_ate_o_passo"].max() > 0


def test_regressao_acumulada_nao_diminui_na_cadeia():
    linhas = []
    for passo, reg in enumerate([0, 2, 0, 0]):
        linhas.append(dict(chain_id=1, mode="incremental", step=passo, reg_failed=reg, status="ok"))
    t = descritiva.regressao_acumulada(pd.DataFrame(linhas)).set_index("step")
    assert t["regressao_acumulada"].tolist() == [0, 1, 1, 1]
    assert t["cadeias_com_regressao_no_passo"].tolist() == [0, 1, 0, 0]


def test_resumo_bate_com_os_dados(df):
    r = descritiva.resumo_da_coleta(df).set_index("mode")
    for modo, g in df.groupby("mode"):
        falhas = g[g["status"] == "falha"]["chain_id"].nunique()
        assert r.loc[modo, "cadeias_censuradas_por_falha"] == falhas
        assert r.loc[modo, "cadeias_completas"] + falhas == 8


def test_tabela_longa_e_tipo_de_pedido(df):
    longa = descritiva.por_passo_completa(df)
    assert longa["unidade"].notna().all()
    tipo = descritiva.por_tipo_de_pedido(df)
    assert set(tipo["request_type"]) == {"cabe", "tensiona"}


def test_diferenca_pareada_tem_ic(df):
    p = models.diferenca_pareada(df)
    ok = p.dropna(subset=["cliffs_ic95_inf"])
    assert (ok["cliffs_ic95_inf"] <= ok["cliffs_delta"] + 1e-9).all()
    assert (ok["cliffs_delta"] <= ok["cliffs_ic95_sup"] + 1e-9).all()


def test_figuras_sao_geradas(df, tmp_path):
    from analysis import survival
    t = survival.tempos_ate_regressao(df)
    km = pd.concat([survival.kaplan_meier(g["tempo"], g["evento"]).assign(mode=m) for m, g in t.groupby("mode")])
    figuras.todas(df, km, models.diferenca_pareada(df), tmp_path)
    assert len(list(tmp_path.glob("*.png"))) == 6
