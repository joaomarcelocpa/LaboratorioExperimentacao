import pandas as pd
import pytest

from analysis.survival import kaplan_meier, log_rank, tempos_ate_regressao

# Freireich et al. (6-MP vs controle), valores de referência clássicos.
T6 = [6, 6, 6, 7, 10, 13, 16, 22, 23, 6, 9, 10, 11, 17, 19, 20, 25, 32, 32, 34, 35]
E6 = [1] * 9 + [0] * 12
CT = [1, 1, 2, 2, 3, 4, 4, 5, 5, 8, 8, 8, 8, 11, 11, 12, 12, 15, 17, 22, 23]


def test_log_rank_bate_com_referencia():
    qui, p = log_rank(T6 + CT, E6 + [1] * 21, ["mp"] * 21 + ["ctl"] * 21)
    assert qui == pytest.approx(16.79, abs=0.01)
    assert p == pytest.approx(4.17e-5, rel=0.01)


def test_kaplan_meier_bate_com_referencia():
    km = kaplan_meier(T6, E6).set_index("tempo")["sobrevivencia"]
    assert km[6] == pytest.approx(0.857, abs=0.001)
    assert km[7] == pytest.approx(0.807, abs=0.001)
    assert km[10] == pytest.approx(0.753, abs=0.001)


def test_log_rank_sem_eventos_nao_rejeita():
    assert log_rank([5, 5, 5, 5], [0, 0, 0, 0], ["a", "a", "b", "b"]) == (0.0, 1.0)


def _linha(c, m, s, reg, status="ok"):
    return dict(chain_id=c, mode=m, step=s, reg_failed=reg, status=status)


def test_tempos_primeira_regressao_censura_e_falha():
    df = pd.DataFrame([
        _linha(1, "incremental", 0, 0), _linha(1, "incremental", 1, 0), _linha(1, "incremental", 2, 3),
        _linha(2, "incremental", 0, 0), _linha(2, "incremental", 1, 0), _linha(2, "incremental", 2, 0),
        _linha(3, "incremental", 0, 0), _linha(3, "incremental", 1, 0), _linha(3, "incremental", 2, 0, "falha"),
    ])
    t = tempos_ate_regressao(df).set_index("chain_id")
    assert (t.loc[1, "tempo"], t.loc[1, "evento"]) == (2, 1)
    assert (t.loc[2, "tempo"], t.loc[2, "evento"]) == (2, 0)  # sem regressão até o fim
    assert (t.loc[3, "tempo"], t.loc[3, "evento"]) == (1, 0)  # falha no passo 2: censura no último ok
