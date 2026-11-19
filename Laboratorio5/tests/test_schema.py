import pandas as pd
import pytest

from analysis import schema
from analysis.synthetic import gerar


@pytest.fixture(scope="module")
def df():
    return gerar(4, seed=1)


def test_sintetico_tem_as_32_colunas_na_ordem(df):
    assert len(schema.NOMES) == 32
    assert tuple(df.columns) == schema.NOMES


def test_sintetico_e_valido(df):
    assert schema.validar(df) == []


def test_ida_e_volta_por_csv_continua_valido(df, tmp_path):
    caminho = tmp_path / "p.csv"
    df.to_csv(caminho, index=False)
    assert schema.validar(schema.carregar(caminho)) == []


def test_coluna_faltando(df):
    erros = schema.validar(df.drop(columns=["flaky"]))
    assert any("flaky" in e for e in erros)


def test_modo_invalido(df):
    ruim = df.copy()
    ruim.loc[0, "mode"] = "outro"
    assert any("mode" in e for e in schema.validar(ruim))


def test_reg_failed_maior_que_total(df):
    ruim = df.copy()
    i = ruim.index[ruim["step"] == 3][0]
    ruim.loc[i, "reg_failed"] = ruim.loc[i, "reg_total"] + 1
    assert any("reg_failed" in e for e in schema.validar(ruim))


def test_linhas_depois_da_falha(df):
    ruim = df.copy()
    i = ruim.index[(ruim["step"] == 2)][0]
    ruim.loc[i, ["status", "build_ok", "run_ok", "retry"]] = ["falha", 0, 0, 1]
    assert any("depois da falha" in e for e in schema.validar(ruim))


def test_passo_repetido(df):
    assert any("repetido" in e for e in schema.validar(pd.concat([df, df.iloc[[5]]])))


def test_versao_que_muda_e_apontada(df):
    ruim = df.copy()
    ruim.loc[ruim.index[-1], "tool_version"] = "outra"
    assert any("tool_version" in e for e in schema.validar(ruim))
