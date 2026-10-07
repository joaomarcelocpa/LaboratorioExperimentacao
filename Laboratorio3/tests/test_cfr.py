"""CFR de CI (RQ 03a) nas três versões."""
import math

import pandas as pd
import pytest

from metricas.cfr import cfr_ci, pct_falhas_flaky


def _run(run_id, classe, workflow_id=1, head_sha="aaa", hora=10, run_attempt=1):
    return {
        "repo": "o/r", "run_id": run_id, "workflow_id": workflow_id,
        "workflow_nome": "CI", "event": "push", "head_sha": head_sha,
        "run_attempt": run_attempt, "conclusion": "x", "classe": classe,
        "inicio": f"2024-10-01T{hora:02d}:00:00Z",
        "fim": f"2024-10-01T{hora:02d}:20:00Z",
        "criado_em": f"2024-10-01T{hora:02d}:00:00Z",
    }


def _tentativa(run_id, tentativa, conclusion="failure", hora=9):
    return {
        "repo": "o/r", "run_id": run_id, "tentativa": tentativa,
        "conclusion": conclusion,
        "inicio": f"2024-10-01T{hora:02d}:00:00Z",
        "fim": f"2024-10-01T{hora:02d}:10:00Z",
    }


def _runs(*linhas):
    return pd.DataFrame(list(linhas))


# --- oficial ------------------------------------------------------------

def test_duas_falhas_e_oito_sucessos_dao_20_por_cento():
    # O exemplo do enunciado.
    linhas = [_run(i, "falha", hora=i) for i in range(2)]
    linhas += [_run(i, "sucesso", hora=i) for i in range(2, 10)]

    assert cfr_ci(pd.DataFrame(linhas)) == pytest.approx(0.2)


def test_ignorados_ficam_fora_do_denominador():
    # cancelled, skipped e conclusion vazio não entram em nenhum cálculo.
    linhas = [
        _run(1, "falha", hora=1), _run(2, "sucesso", hora=2),
        _run(3, "ignorado", hora=3), _run(4, "ignorado", hora=4),
        _run(5, "ignorado", hora=5),
    ]

    assert cfr_ci(pd.DataFrame(linhas)) == pytest.approx(0.5)


def test_sem_sucesso_nem_falha_e_nan():
    # Zero diria "nenhuma mudança falhou", que é diferente de "não há dados".
    assert math.isnan(cfr_ci(_runs(_run(1, "ignorado"))))


def test_frame_vazio_e_nan():
    assert math.isnan(cfr_ci(pd.DataFrame(columns=["repo", "classe"])))


# --- bruto --------------------------------------------------------------

def test_bruto_inclui_as_tentativas_anteriores():
    # O run passou na tentativa 2, então o oficial não vê falha nenhuma.
    runs = _runs(_run(1, "sucesso", run_attempt=2, hora=10))
    attempts = pd.DataFrame([_tentativa(1, 1, hora=9)])

    assert cfr_ci(runs) == pytest.approx(0.0)
    assert cfr_ci(runs, attempts) == pytest.approx(0.5)


def test_tentativa_ignorada_nao_entra_no_bruto():
    runs = _runs(_run(1, "sucesso", run_attempt=2, hora=10))
    attempts = pd.DataFrame([_tentativa(1, 1, conclusion="cancelled", hora=9)])

    assert cfr_ci(runs, attempts) == pytest.approx(0.0)


def test_timed_out_e_startup_failure_contam_como_falha():
    runs = _runs(_run(1, "sucesso", run_attempt=3, hora=10))
    attempts = pd.DataFrame([
        _tentativa(1, 1, conclusion="timed_out", hora=8),
        _tentativa(1, 2, conclusion="startup_failure", hora=9),
    ])

    assert cfr_ci(runs, attempts) == pytest.approx(2 / 3)


# --- sem flaky ----------------------------------------------------------

def test_rerun_que_passa_reduz_o_cfr_sem_flaky():
    # O caso central da E2: a falha da tentativa 1 foi instabilidade, não
    # defeito, porque a tentativa 2 passou no mesmo head_sha.
    runs = _runs(_run(1, "sucesso", run_attempt=2, hora=10))
    attempts = pd.DataFrame([_tentativa(1, 1, hora=9)])

    assert cfr_ci(runs, attempts) == pytest.approx(0.5)
    assert cfr_ci(runs, attempts, sem_flaky=True) == pytest.approx(0.0)


def test_falha_sem_sucesso_posterior_sobrevive_ao_filtro():
    runs = _runs(_run(1, "falha", hora=10), _run(2, "sucesso", head_sha="bbb", hora=11))

    assert cfr_ci(runs, sem_flaky=True) == pytest.approx(0.5)


def test_sem_flaky_deriva_do_bruto_e_nao_do_oficial():
    # Duas falhas: uma recuperada por re-run (flaky), outra não.
    runs = _runs(
        _run(1, "sucesso", run_attempt=2, head_sha="aaa", hora=10),
        _run(2, "falha", head_sha="bbb", hora=11),
    )
    attempts = pd.DataFrame([_tentativa(1, 1, hora=9)])

    assert cfr_ci(runs) == pytest.approx(0.5), "oficial: só vê a falha de bbb"
    assert cfr_ci(runs, attempts) == pytest.approx(2 / 3), "bruto: vê as duas"
    assert cfr_ci(runs, attempts, sem_flaky=True) == pytest.approx(0.5), \
        "sem flaky: tira a de aaa, sobra a de bbb sobre 2 execuções"


# --- pct_falhas_flaky ---------------------------------------------------

def test_pct_falhas_flaky_sobre_o_bruto():
    runs = _runs(
        _run(1, "sucesso", run_attempt=2, head_sha="aaa", hora=10),
        _run(2, "falha", head_sha="bbb", hora=11),
    )
    attempts = pd.DataFrame([_tentativa(1, 1, hora=9)])

    assert pct_falhas_flaky(runs, attempts) == pytest.approx(0.5)


def test_pct_falhas_flaky_sem_falha_nenhuma_e_nan():
    # Zero diria "nenhuma falha era flaky"; NaN diz "não houve falhas".
    assert math.isnan(pct_falhas_flaky(_runs(_run(1, "sucesso"))))


def test_pct_falhas_flaky_tudo_flaky_e_um():
    runs = _runs(_run(1, "sucesso", run_attempt=2, hora=10))
    attempts = pd.DataFrame([_tentativa(1, 1, hora=9)])

    assert pct_falhas_flaky(runs, attempts) == pytest.approx(1.0)
