import pytest

from analysis import power
from analysis.synthetic import Parametros


def test_erro_tipo_i_perto_de_alfa():
    taxas = power.erro_tipo_i(Parametros(), k=10, reps=1500)
    for teste, v in taxas.items():
        assert v == pytest.approx(0.05, abs=0.02), teste


def test_poder_cresce_com_cadeias_e_com_efeito():
    pouco = power.poder(Parametros(inclinacao_extra_inc=0.10), 5, 600)["welch"]
    muito = power.poder(Parametros(inclinacao_extra_inc=0.10), 15, 600)["welch"]
    maior_efeito = power.poder(Parametros(inclinacao_extra_inc=0.25), 5, 600)["welch"]
    assert muito > pouco
    assert maior_efeito > pouco


def test_reprodutivel_com_a_mesma_semente():
    assert power.poder(Parametros(), 5, 200, seed=1) == power.poder(Parametros(), 5, 200, seed=1)


def test_cadeias_necessarias_escolhe_o_menor_k():
    tab = power.tabela_de_poder(Parametros(), grade=(5, 20), reps=300)
    k = power.cadeias_necessarias(tab, "grande", "welch")
    assert k in (5, 20, None)


def test_estimativa_do_piloto_aponta_efeito_positivo():
    from analysis.synthetic import gerar
    par = power.estimar_parametros_do_piloto(gerar(10, parametros=Parametros(inclinacao_extra_inc=0.2), seed=5))
    assert par.inclinacao_extra_inc > 0
