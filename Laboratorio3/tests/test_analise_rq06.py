import pandas as pd
import pytest
from analise.rq06 import quartis_labels, mapear_linguagem


# --- quartis_labels ---

def test_quartis_retorna_4_grupos():
    s = pd.Series(range(100))
    grupos = quartis_labels(s)
    assert set(grupos.dropna().unique()) == {"Q1", "Q2", "Q3", "Q4"}


def test_quartis_tamanho_igual_ao_input():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    assert len(quartis_labels(s)) == 4


def test_quartis_propaga_nan():
    s = pd.Series([1.0, float("nan"), 3.0, 4.0, 5.0])
    grupos = quartis_labels(s)
    assert grupos.isna().sum() == 1


# --- mapear_linguagem ---

def test_mapear_linguagem_top3_agrupa_restantes():
    s = pd.Series(["Python"] * 5 + ["Go"] * 3 + ["Java"] * 2 + ["Rust"] * 1)
    resultado = mapear_linguagem(s, top_n=2)
    assert set(resultado.unique()) == {"Python", "Go", "Outras"}


def test_mapear_linguagem_sem_outras_se_todos_no_top():
    s = pd.Series(["Python"] * 5 + ["Go"] * 3)
    resultado = mapear_linguagem(s, top_n=5)
    assert "Outras" not in resultado.values


def test_mapear_linguagem_preserva_tamanho():
    s = pd.Series(["Python"] * 3 + ["Go"] * 2 + ["Rust"] * 1)
    assert len(mapear_linguagem(s, top_n=2)) == 6


# --- testar_kruskal / testar_mann_whitney / testar_fator_metrica ---

from analise.rq06 import (
    testar_kruskal as _kruskal,
    testar_mann_whitney as _mann_whitney,
    testar_fator_metrica as _fator_metrica,
)


def test_kruskal_grupos_iguais_p_alto():
    g = {"A": pd.Series([1.0, 2.0, 3.0]), "B": pd.Series([1.0, 2.0, 3.0])}
    r = _kruskal(g)
    assert r["pvalue"] > 0.05


def test_kruskal_grupos_distintos_p_baixo():
    g = {"A": pd.Series([1.0, 2.0, 3.0]), "B": pd.Series([100.0, 200.0, 300.0])}
    r = _kruskal(g)
    assert r["pvalue"] < 0.05


def test_kruskal_epsilon2_entre_0_e_1():
    g = {"A": pd.Series([1.0, 2.0, 3.0]), "B": pd.Series([4.0, 5.0, 6.0])}
    r = _kruskal(g)
    assert 0.0 <= r["epsilon2"] <= 1.0


def test_kruskal_n_total_correto():
    g = {"A": pd.Series([1.0, 2.0]), "B": pd.Series([3.0, 4.0, 5.0])}
    r = _kruskal(g)
    assert r["n_total"] == 5


def test_mann_whitney_cliff_delta_range():
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([4.0, 5.0, 6.0])
    r = _mann_whitney(x, y)
    assert -1.0 <= r["cliff_delta"] <= 1.0


def test_mann_whitney_grupos_iguais_delta_zero():
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([1.0, 2.0, 3.0])
    r = _mann_whitney(x, y)
    assert abs(r["cliff_delta"]) < 1e-9


def test_mann_whitney_n_correto():
    x = pd.Series([1.0, 2.0])
    y = pd.Series([3.0, 4.0, 5.0])
    r = _mann_whitney(x, y)
    assert r["n1"] == 2 and r["n2"] == 3


def test_fator_metrica_dois_grupos_usa_mann_whitney():
    df = pd.DataFrame({
        "fator": ["A"] * 5 + ["B"] * 5,
        "metrica": list(range(5)) + list(range(10, 15)),
    })
    r = _fator_metrica(df, "fator", "metrica")
    assert r["teste"] == "mann_whitney"
    assert "cliff_delta" in r


def test_fator_metrica_tres_grupos_usa_kruskal():
    df = pd.DataFrame({
        "fator": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
        "metrica": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
    })
    r = _fator_metrica(df, "fator", "metrica")
    assert r["teste"] == "kruskal"
    assert "epsilon2" in r


def test_fator_metrica_descarta_nan_na_metrica():
    # A tem 2 válidos (NaN descartado), B tem 2 válidos → n_total=4
    df = pd.DataFrame({
        "fator": ["A", "A", "A", "B", "B"],
        "metrica": [1.0, float("nan"), 2.0, 3.0, 4.0],
    })
    r = _fator_metrica(df, "fator", "metrica")
    assert r["n_total"] == 4
