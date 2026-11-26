from collections import Counter

import pytest

from harness.plano_execucao import MAQUINAS, MODOS, ORDENS, gerar


def test_balanceado_por_modo_ordem_e_maquina():
    plano = gerar(12, semente=118)
    assert len(plano) == 24
    cont = Counter((c["modo"], c["ordem"], c["maquina"]) for c in plano)
    assert set(cont.values()) == {2}
    assert len(cont) == len(MODOS) * len(ORDENS) * len(MAQUINAS)


def test_reproduzivel_e_depende_da_semente():
    assert gerar(12, 118) == gerar(12, 118)
    assert gerar(12, 118) != gerar(12, 119)


def test_posicoes_formam_fila_por_maquina():
    plano = gerar(18, 118)
    for m in MAQUINAS:
        posicoes = sorted(c["posicao_na_maquina"] for c in plano if c["maquina"] == m)
        assert posicoes == list(range(1, len(posicoes) + 1))


def test_ids_unicos():
    plano = gerar(18, 118)
    assert len({c["cadeia_id"] for c in plano}) == len(plano)


def test_rejeita_numero_que_desbalanceia():
    with pytest.raises(ValueError):
        gerar(15, 118)
