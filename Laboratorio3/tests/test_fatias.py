"""Fatiamento da janela: meses, bissecção e a sintaxe do created=."""
from datetime import date, datetime, timedelta, timezone

import pytest

from coleta.runs import PISO_DA_FATIA, Fatia, meses


def _dt(ano, mes, dia, h=0, m=0, s=0):
    return datetime(ano, mes, dia, h, m, s, tzinfo=timezone.utc)


# --- meses --------------------------------------------------------------

def test_doze_meses_de_uma_janela_cheia():
    fatias = meses(date(2024, 10, 1), date(2025, 9, 30))

    assert len(fatias) == 12
    assert fatias[0].inicio == _dt(2024, 10, 1)
    assert fatias[-1].fim == _dt(2025, 9, 30, 23, 59, 59)


def test_fatias_nao_deixam_buraco_nem_sobrepoem():
    fatias = meses(date(2024, 10, 1), date(2025, 9, 30))

    for anterior, seguinte in zip(fatias, fatias[1:]):
        assert seguinte.inicio - anterior.fim == timedelta(seconds=1), (
            f"buraco ou sobreposição entre {anterior.fim} e {seguinte.inicio}"
        )


def test_primeira_fatia_e_recortada_no_inicio_da_janela():
    # Se a janela começa no dia 15, a primeira fatia não pode começar no dia
    # 1: puxaria runs de fora da janela e enviesaria a amostra inteira.
    fatias = meses(date(2024, 10, 15), date(2024, 12, 31))

    assert fatias[0].inicio == _dt(2024, 10, 15)
    assert fatias[0].fim == _dt(2024, 10, 31, 23, 59, 59)


def test_ultima_fatia_e_recortada_no_fim_da_janela():
    fatias = meses(date(2024, 10, 1), date(2024, 12, 10))

    assert fatias[-1].fim == _dt(2024, 12, 10, 23, 59, 59)
    assert len(fatias) == 3


def test_fevereiro_de_ano_bissexto_tem_29_dias():
    fatias = meses(date(2024, 2, 1), date(2024, 2, 29))

    assert len(fatias) == 1
    assert fatias[0].fim == _dt(2024, 2, 29, 23, 59, 59)


def test_fevereiro_de_ano_comum_tem_28_dias():
    fatias = meses(date(2025, 2, 1), date(2025, 3, 1))

    assert fatias[0].fim == _dt(2025, 2, 28, 23, 59, 59)
    assert fatias[1].inicio == _dt(2025, 3, 1)


def test_janela_de_um_dia_so():
    fatias = meses(date(2024, 10, 5), date(2024, 10, 5))

    assert len(fatias) == 1
    assert fatias[0].inicio == _dt(2024, 10, 5)
    assert fatias[0].fim == _dt(2024, 10, 5, 23, 59, 59)


def test_janela_invertida_e_erro():
    with pytest.raises(ValueError, match="anterior"):
        meses(date(2024, 10, 31), date(2024, 10, 1))


# --- bissecção ----------------------------------------------------------

def test_partir_um_mes_da_duas_quinzenas():
    outubro = Fatia(_dt(2024, 10, 1), _dt(2024, 10, 31, 23, 59, 59))

    primeira, segunda = outubro.partir()

    assert primeira.inicio == outubro.inicio
    assert segunda.fim == outubro.fim
    assert segunda.inicio - primeira.fim == timedelta(seconds=1)
    assert timedelta(days=15) <= primeira.duracao() <= timedelta(days=16)


def test_partir_uma_quinzena_da_duas_semanas():
    quinzena = Fatia(_dt(2024, 10, 1), _dt(2024, 10, 15, 23, 59, 59))

    primeira, segunda = quinzena.partir()

    assert timedelta(days=7) <= primeira.duracao() <= timedelta(days=8)
    assert timedelta(days=7) <= segunda.duracao() <= timedelta(days=8)


def test_as_metades_somam_o_todo():
    fatia = Fatia(_dt(2024, 10, 1), _dt(2024, 10, 31, 23, 59, 59))

    primeira, segunda = fatia.partir()

    assert primeira.duracao() + segunda.duracao() == fatia.duracao()


def test_uma_hora_nao_se_parte():
    # O piso: abaixo disto a subdivisão para e a fatia vira diagnóstico.
    uma_hora = Fatia(_dt(2024, 10, 1, 0), _dt(2024, 10, 1, 0, 59, 59))

    assert uma_hora.duracao() == PISO_DA_FATIA
    assert uma_hora.partir() is None


def test_duas_horas_ainda_se_partem():
    duas_horas = Fatia(_dt(2024, 10, 1, 0), _dt(2024, 10, 1, 1, 59, 59))

    primeira, segunda = duas_horas.partir()

    assert primeira.duracao() == PISO_DA_FATIA
    assert segunda.duracao() == PISO_DA_FATIA


# --- sintaxe do created= ------------------------------------------------

def test_fatia_de_dias_inteiros_usa_a_forma_de_data():
    # É a forma do enunciado, e é a que a API aceita com certeza.
    fatia = Fatia(_dt(2024, 10, 1), _dt(2024, 10, 31, 23, 59, 59))

    assert fatia.created() == "2024-10-01..2024-10-31"
    assert fatia.e_de_dias_inteiros() is True


def test_fatia_com_hora_usa_a_forma_iso():
    fatia = Fatia(_dt(2024, 10, 1, 0), _dt(2024, 10, 1, 11, 59, 59))

    assert fatia.created() == "2024-10-01T00:00:00Z..2024-10-01T11:59:59Z"
    assert fatia.e_de_dias_inteiros() is False


def test_um_dia_inteiro_ainda_e_forma_de_data():
    fatia = Fatia(_dt(2024, 10, 5), _dt(2024, 10, 5, 23, 59, 59))

    assert fatia.created() == "2024-10-05..2024-10-05"
