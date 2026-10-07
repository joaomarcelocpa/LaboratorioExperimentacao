import pandas as pd
import pytest

from pipeline.estimativa import estimar


def _custo(*linhas):
    return pd.DataFrame(linhas, columns=["endpoint", "chamadas", "do_cache"])


def test_dez_repos_mil_chamadas_seiscentos_segundos_para_300():
    custo = _custo(("/repos/{owner}/{repo}/actions/runs", 800, 0),
                   ("/repos/{owner}/{repo}/releases", 200, 50))
    r = estimar(custo, n_medido=10, n_alvo=300, segundos=600)
    assert r["chamadas_por_repo"] == 100
    assert r["chamadas_alvo"] == 30000
    assert r["horas_por_tempo"] == pytest.approx(5.0)
    assert r["horas_por_cota"] == pytest.approx(6.0)
    assert r["horas_estimadas"] == pytest.approx(6.0)
    assert r["endpoint_mais_caro"] == "/repos/{owner}/{repo}/actions/runs"


def test_tempo_pode_dominar_a_cota():
    custo = _custo(("/x", 100, 0))
    r = estimar(custo, n_medido=10, n_alvo=300, segundos=7200)
    assert r["horas_estimadas"] == r["horas_por_tempo"] == pytest.approx(60.0)


def test_so_cache_estima_zero_chamadas_sem_dividir_por_zero():
    r = estimar(_custo(("/x", 0, 40)), n_medido=10, n_alvo=300, segundos=5)
    assert r["chamadas_alvo"] == 0
    assert r["horas_por_cota"] == 0.0


def test_custo_vazio_nao_tem_endpoint_mais_caro():
    r = estimar(_custo(), n_medido=10, n_alvo=300, segundos=5)
    assert r["endpoint_mais_caro"] is None


@pytest.mark.parametrize("n", [0, -1])
def test_n_medido_invalido(n):
    with pytest.raises(ValueError):
        estimar(_custo(("/x", 1, 0)), n_medido=n, n_alvo=300, segundos=1)
