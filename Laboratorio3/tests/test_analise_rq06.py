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
