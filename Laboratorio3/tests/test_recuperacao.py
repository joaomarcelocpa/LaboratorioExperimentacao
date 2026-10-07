"""Episódios de falha e tempo de recuperação (RQ 04)."""
import math

import pandas as pd
import pytest

from metricas.recuperacao import (
    episodios, mediana_horas, pct_censurados, recuperacao_sem_flaky,
)
from metricas.schemas import SCHEMAS, validar


def _run(run_id, classe, hora, minuto=0, fim_hora=None, fim_minuto=None,
         workflow_id=1, head_sha="aaa", run_attempt=1):
    fim_hora = hora if fim_hora is None else fim_hora
    fim_minuto = minuto if fim_minuto is None else fim_minuto
    return {
        "repo": "o/r", "run_id": run_id, "workflow_id": workflow_id,
        "workflow_nome": "CI", "event": "push", "head_sha": head_sha,
        "run_attempt": run_attempt, "conclusion": "x", "classe": classe,
        "inicio": f"2024-10-01T{hora:02d}:{minuto:02d}:00Z",
        "fim": f"2024-10-01T{fim_hora:02d}:{fim_minuto:02d}:00Z",
        "criado_em": f"2024-10-01T{hora:02d}:{minuto:02d}:00Z",
    }


def _runs(*linhas):
    return pd.DataFrame(list(linhas))


# --- o exemplo do enunciado ---------------------------------------------

def test_exemplo_do_enunciado_da_uma_hora_e_vinte():
    # 09:00 success | 10:00 failure (inicio) | 10:30 failure | 11:15 success,
    # terminando 11:20. Recuperação = 11:20 - 10:00 = 1h20.
    runs = _runs(
        _run(1, "sucesso", 9),
        _run(2, "falha", 10),
        _run(3, "falha", 10, 30),
        _run(4, "sucesso", 11, 15, fim_hora=11, fim_minuto=20),
    )

    df = episodios(runs).df

    assert len(df) == 1, "falhas consecutivas são um episódio só"
    assert df.iloc[0]["horas"] == pytest.approx(1 + 20 / 60)
    assert not df.iloc[0]["censurado"]


# --- separação por workflow ---------------------------------------------

def test_workflows_intercalados_nao_se_misturam():
    runs = _runs(
        _run(1, "sucesso", 9, workflow_id=1),
        _run(2, "sucesso", 9, minuto=30, workflow_id=2),
        _run(3, "falha", 10, workflow_id=1),
        _run(4, "falha", 10, minuto=30, workflow_id=2),
        _run(5, "sucesso", 11, fim_hora=11, fim_minuto=0, workflow_id=1),
        _run(6, "sucesso", 13, fim_hora=13, fim_minuto=0, workflow_id=2),
    )

    df = episodios(runs).df.sort_values("workflow_id").reset_index(drop=True)

    assert len(df) == 2
    assert df.iloc[0]["horas"] == pytest.approx(1.0)
    assert df.iloc[1]["horas"] == pytest.approx(2.5)


# --- censura ------------------------------------------------------------

def test_falha_nunca_recuperada_e_censurada():
    runs = _runs(_run(1, "sucesso", 9), _run(2, "falha", 10))

    df = episodios(runs).df

    assert len(df) == 1
    assert df.iloc[0]["censurado"]
    assert pd.isna(df.iloc[0]["fim"])
    assert pd.isna(df.iloc[0]["horas"])


def test_censurados_ficam_fora_da_mediana():
    # Um censurado não tem duração conhecida: entrar com a duração parcial
    # puxaria a mediana para baixo e faria o repo parecer melhor do que é.
    # O frame é montado à mão com horas PREENCHIDAS no censurado — se o
    # teste viesse de episodios(), o NaN que _censurado grava faria o
    # median() do pandas excluí-lo sozinho e o filtro não seria provado.
    df = pd.DataFrame([
        {"repo": "o/r", "workflow_id": 1, "inicio": pd.Timestamp("2024-10-01T10:00:00Z"),
         "fim": pd.Timestamp("2024-10-01T12:00:00Z"), "horas": 2.0,
         "censurado": False, "so_flaky": False},
        {"repo": "o/r", "workflow_id": 1, "inicio": pd.Timestamp("2024-10-01T13:00:00Z"),
         "fim": pd.NaT, "horas": 0.1,
         "censurado": True, "so_flaky": False},
    ])

    assert mediana_horas(df) == pytest.approx(2.0),         "a duração parcial do censurado entrou na mediana"


def test_episodios_de_verdade_marcam_censura_e_contam_certo():
    runs = _runs(
        _run(1, "sucesso", 9), _run(2, "falha", 10),
        _run(3, "sucesso", 12, fim_hora=12), _run(4, "falha", 13),
    )

    df = episodios(runs).df

    assert len(df) == 2
    assert mediana_horas(df) == pytest.approx(2.0)


def test_pct_censurados():
    runs = _runs(
        _run(1, "sucesso", 9), _run(2, "falha", 10),
        _run(3, "sucesso", 12, fim_hora=12), _run(4, "falha", 13),
    )

    assert pct_censurados(episodios(runs).df) == pytest.approx(0.5)


def test_pct_censurados_sem_episodio_e_nan():
    assert math.isnan(pct_censurados(episodios(_runs(_run(1, "sucesso", 9))).df))


# --- censura à esquerda -------------------------------------------------

def test_falha_antes_do_primeiro_sucesso_nao_abre_episodio():
    # O enunciado exige "primeira falha APÓS um sucesso": um workflow que
    # entra na janela já quebrado não diz quando quebrou.
    runs = _runs(_run(1, "falha", 9), _run(2, "falha", 10),
                 _run(3, "sucesso", 11, fim_hora=11))

    resultado = episodios(runs)

    assert len(resultado.df) == 0
    assert resultado.falhas_sem_sucesso_anterior == 2


def test_falhas_de_esquerda_sao_contadas_e_nao_descartadas():
    # Descartá-las em silêncio faria os repos parecerem mais estáveis.
    runs = _runs(_run(1, "falha", 9), _run(2, "sucesso", 10, fim_hora=10),
                 _run(3, "falha", 11), _run(4, "sucesso", 12, fim_hora=12))

    resultado = episodios(runs)

    assert resultado.falhas_sem_sucesso_anterior == 1
    assert len(resultado.df) == 1, "o episódio depois do primeiro sucesso conta"


# --- flaky --------------------------------------------------------------

def test_episodio_e_so_flaky_quando_um_novo_run_no_mesmo_sha_passa():
    # runs.csv esconde o re-run DENTRO do run, mas um novo run no mesmo sha
    # é visível — e torna flaky a falha do episódio anterior.
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 10, head_sha="bbb"),
        _run(3, "sucesso", 11, fim_hora=11, head_sha="bbb"),
    )

    assert episodios(runs).df.iloc[0]["so_flaky"]


def test_episodio_com_sha_diferente_nao_e_so_flaky():
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 10, head_sha="bbb"),
        _run(3, "sucesso", 11, fim_hora=11, head_sha="ccc"),
    )

    assert not episodios(runs).df.iloc[0]["so_flaky"]


def test_recuperacao_sem_flaky_descarta_os_episodios_so_flaky():
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 10, head_sha="bbb"),
        _run(3, "sucesso", 11, fim_hora=11, head_sha="bbb"),
        _run(4, "falha", 12, head_sha="ccc"),
        _run(5, "sucesso", 15, fim_hora=15, head_sha="ddd"),
    )

    assert mediana_horas(episodios(runs).df) == pytest.approx(2.0)
    assert recuperacao_sem_flaky(runs) == pytest.approx(3.0)


# --- contrato e bordas --------------------------------------------------

def test_episodios_respeita_o_contrato():
    runs = _runs(_run(1, "sucesso", 9), _run(2, "falha", 10),
                 _run(3, "sucesso", 11, fim_hora=11))

    df = episodios(runs).df

    validar(df, SCHEMAS["episodios"])
    assert list(df.columns) == list(SCHEMAS["episodios"].colunas)


def test_sem_runs_devolve_frame_vazio_valido():
    df = episodios(pd.DataFrame(columns=["repo", "classe"])).df

    validar(df, SCHEMAS["episodios"])
    assert df.empty


def test_mediana_sem_episodio_e_nan():
    assert math.isnan(mediana_horas(episodios(_runs(_run(1, "sucesso", 9))).df))


def test_ignorados_nao_abrem_nem_fecham_episodio():
    runs = _runs(
        _run(1, "sucesso", 9), _run(2, "ignorado", 9, minuto=30),
        _run(3, "falha", 10), _run(4, "ignorado", 10, minuto=30),
        _run(5, "sucesso", 11, fim_hora=11),
    )

    df = episodios(runs).df

    assert len(df) == 1
    assert df.iloc[0]["horas"] == pytest.approx(1.0)


# --- achados da revisão: a hierarquia das duas populações ---------------

def _tentativa(run_id, tentativa, conclusion="failure", hora=10, minuto=0):
    return {
        "repo": "o/r", "run_id": run_id, "tentativa": tentativa,
        "conclusion": conclusion,
        "inicio": f"2024-10-01T{hora:02d}:{minuto:02d}:00Z",
        "fim": f"2024-10-01T{hora:02d}:{minuto + 10:02d}:00Z",
    }


def test_episodios_ignora_as_tentativas_e_fica_so_com_os_runs():
    # episodios.csv é o conjunto da RQ 04, sobre runs.csv. Se a tentativa
    # entrasse, o episódio abriria às 10:00 em vez de às 11:00.
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 11, head_sha="bbb", run_attempt=2),
        _run(3, "sucesso", 14, fim_hora=14, head_sha="ccc"),
    )
    attempts = pd.DataFrame([_tentativa(2, 1, hora=10)])

    df = episodios(runs, attempts).df

    assert len(df) == 1
    assert df.iloc[0]["horas"] == pytest.approx(3.0), \
        "o episódio tem que abrir na falha do run (11:00), não na da tentativa"


def test_recuperacao_sem_flaky_usa_a_linha_do_tempo_bruta():
    # A mesma entrada do teste acima: aqui a tentativa CONTA, e o episódio
    # abre às 10:00. As duas colunas medem populações diferentes.
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 11, head_sha="bbb", run_attempt=2),
        _run(3, "sucesso", 14, fim_hora=14, head_sha="ccc"),
    )
    attempts = pd.DataFrame([_tentativa(2, 1, hora=10)])

    assert mediana_horas(episodios(runs, attempts).df) == pytest.approx(3.0)
    assert recuperacao_sem_flaky(runs, attempts) == pytest.approx(4.0)


def test_so_flaky_exige_que_TODAS_as_falhas_sejam_flaky():
    # Um episódio com uma falha flaky e outra não é um episódio com defeito
    # de verdade dentro. `any` o descartaria da recuperacao_sem_flaky.
    runs = _runs(
        _run(1, "sucesso", 9, head_sha="aaa"),
        _run(2, "falha", 10, head_sha="bbb"),
        _run(3, "falha", 10, minuto=30, head_sha="ccc"),
        _run(4, "sucesso", 11, fim_hora=11, head_sha="bbb"),
    )

    df = episodios(runs).df

    assert len(df) == 1
    assert not df.iloc[0]["so_flaky"], \
        "a falha de ccc não teve sucesso posterior: o episódio não é só flaky"


def test_sucesso_sem_fim_vira_episodio_censurado():
    # fim vazio significa que não se sabe quando a recuperação terminou.
    # Fechar o episódio com horas=NaN e censurado=False o faria sumir dos
    # dois cálculos e contradiria o CSV, onde fim vazio é censura.
    runs = _runs(_run(1, "sucesso", 9), _run(2, "falha", 10),
                 _run(3, "sucesso", 11))
    runs.loc[runs["run_id"] == 3, "fim"] = None

    df = episodios(runs).df

    assert df.iloc[0]["censurado"], "sem fim conhecido, o episódio é censurado"
    assert pct_censurados(df) == pytest.approx(1.0)
