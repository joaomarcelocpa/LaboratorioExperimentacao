"""Linha do tempo unificada e marcação de flaky."""
import pandas as pd
import pytest

from metricas.execucoes import COLUNAS_EXECUCAO, linha_do_tempo, marcar_flaky


def _run(run_id, classe="sucesso", workflow_id=1, head_sha="aaa",
         inicio="2024-10-01T10:00:00Z", run_attempt=1, criado_em=None):
    return {
        "repo": "o/r", "run_id": run_id, "workflow_id": workflow_id,
        "workflow_nome": "CI", "event": "push", "head_sha": head_sha,
        "run_attempt": run_attempt,
        "conclusion": {"sucesso": "success", "falha": "failure"}.get(classe, "cancelled"),
        "classe": classe, "inicio": inicio,
        "fim": inicio.replace("10:00", "10:20"),
        "criado_em": criado_em or inicio,
    }


def _tentativa(run_id, tentativa, conclusion="failure", inicio="2024-10-01T09:00:00Z"):
    return {
        "repo": "o/r", "run_id": run_id, "tentativa": tentativa,
        "conclusion": conclusion, "inicio": inicio,
        "fim": inicio.replace("09:00", "09:10"),
    }


def _df(linhas):
    return pd.DataFrame(linhas)


# --- montagem da linha do tempo -----------------------------------------

def test_so_runs_vira_linha_do_tempo():
    exec_ = linha_do_tempo(_df([_run(1), _run(2)]))

    assert list(exec_.columns) == COLUNAS_EXECUCAO
    assert len(exec_) == 2
    assert set(exec_["origem"]) == {"run"}


def test_tentativas_herdam_workflow_id_e_head_sha_do_run():
    # run_attempts.csv não tem nenhum dos dois: eles vêm da junção por run_id.
    runs = _df([_run(7, workflow_id=99, head_sha="bbb", run_attempt=2)])
    attempts = _df([_tentativa(7, 1)])

    exec_ = linha_do_tempo(runs, attempts)

    tentativa = exec_[exec_["origem"] == "tentativa"].iloc[0]
    assert tentativa["workflow_id"] == 99
    assert tentativa["head_sha"] == "bbb"


def test_tentativa_e_classificada_pela_tabela_da_secao_3():
    runs = _df([_run(1, run_attempt=2)])
    attempts = _df([_tentativa(1, 1, conclusion="timed_out")])

    exec_ = linha_do_tempo(runs, attempts)

    assert exec_[exec_["origem"] == "tentativa"].iloc[0]["classe"] == "falha"


def test_ordena_no_tempo():
    exec_ = linha_do_tempo(_df([
        _run(1, inicio="2024-10-03T10:00:00Z"),
        _run(2, inicio="2024-10-01T10:00:00Z"),
    ]))

    assert exec_.iloc[0]["inicio"] < exec_.iloc[1]["inicio"]


def test_conclusion_ausente_na_tentativa_nao_estoura():
    # pd.read_csv devolve NaN para célula vazia, e NaN é truthy: o
    # `(conclusion or "")` de classificar deixaria o NaN passar e o .strip()
    # seguinte levantaria AttributeError no meio do cálculo.
    runs = _df([_run(1, run_attempt=2)])
    attempts = _df([_tentativa(1, 1)])
    attempts["conclusion"] = float("nan")

    exec_ = linha_do_tempo(runs, attempts)

    assert exec_[exec_["origem"] == "tentativa"].iloc[0]["classe"] == "ignorado"


def test_tentativa_vem_antes_do_seu_run():
    runs = _df([_run(1, run_attempt=2, inicio="2024-10-01T10:00:00Z")])
    attempts = _df([_tentativa(1, 1, inicio="2024-10-01T09:00:00Z")])

    exec_ = linha_do_tempo(runs, attempts)

    assert list(exec_["origem"]) == ["tentativa", "run"]


def test_tentativa_orfa_e_descartada():
    # run_id que não existe em runs: a junção daria workflow_id nulo e a
    # linha corromperia os grupos de flaky e os episódios.
    runs = _df([_run(1)])
    attempts = _df([_tentativa(999, 1)])

    exec_ = linha_do_tempo(runs, attempts)

    assert len(exec_) == 1
    assert set(exec_["origem"]) == {"run"}


def test_aceita_datas_como_texto_e_como_datetime():
    # pd.read_csv devolve texto; um chamador pode já ter convertido.
    texto = _df([_run(1, inicio="2024-10-01T10:00:00Z")])
    convertido = texto.copy()
    convertido["inicio"] = pd.to_datetime(convertido["inicio"], utc=True)
    convertido["fim"] = pd.to_datetime(convertido["fim"], utc=True)

    assert linha_do_tempo(texto).iloc[0]["inicio"] == \
        linha_do_tempo(convertido).iloc[0]["inicio"]


def test_runs_vazio_devolve_frame_vazio_com_as_colunas():
    exec_ = linha_do_tempo(pd.DataFrame(columns=["repo", "run_id"]))

    assert list(exec_.columns) == COLUNAS_EXECUCAO
    assert exec_.empty


# --- marcação de flaky --------------------------------------------------

def test_falha_seguida_de_sucesso_no_mesmo_sha_e_flaky():
    runs = _df([
        _run(1, "falha", inicio="2024-10-01T10:00:00Z"),
        _run(2, "sucesso", inicio="2024-10-01T11:00:00Z"),
    ])

    marcado = marcar_flaky(linha_do_tempo(runs))

    assert list(marcado["flaky"]) == [True, False]


def test_falha_falha_sucesso_marca_as_duas_falhas():
    # O mesmo código acabou passando sem alteração: nenhuma das duas era
    # defeito. Esta é a regra "qualquer sucesso posterior", não "o adjacente".
    runs = _df([
        _run(1, "falha", inicio="2024-10-01T10:00:00Z"),
        _run(2, "falha", inicio="2024-10-01T11:00:00Z"),
        _run(3, "sucesso", inicio="2024-10-01T12:00:00Z"),
    ])

    marcado = marcar_flaky(linha_do_tempo(runs))

    assert list(marcado["flaky"]) == [True, True, False]


def test_ignorado_entre_a_falha_e_o_sucesso_nao_quebra_a_cadeia():
    runs = _df([
        _run(1, "falha", inicio="2024-10-01T10:00:00Z"),
        _run(2, "ignorado", inicio="2024-10-01T11:00:00Z"),
        _run(3, "sucesso", inicio="2024-10-01T12:00:00Z"),
    ])

    assert marcar_flaky(linha_do_tempo(runs)).iloc[0]["flaky"]


def test_sucesso_anterior_nao_torna_a_falha_flaky():
    # A ordem importa: passou, depois quebrou. Isso é defeito, não flaky.
    runs = _df([
        _run(1, "sucesso", inicio="2024-10-01T10:00:00Z"),
        _run(2, "falha", inicio="2024-10-01T11:00:00Z"),
    ])

    assert list(marcar_flaky(linha_do_tempo(runs))["flaky"]) == [False, False]


def test_head_sha_diferente_nao_contamina():
    runs = _df([
        _run(1, "falha", head_sha="aaa", inicio="2024-10-01T10:00:00Z"),
        _run(2, "sucesso", head_sha="bbb", inicio="2024-10-01T11:00:00Z"),
    ])

    assert not marcar_flaky(linha_do_tempo(runs)).iloc[0]["flaky"]


def test_workflow_diferente_nao_contamina():
    runs = _df([
        _run(1, "falha", workflow_id=1, inicio="2024-10-01T10:00:00Z"),
        _run(2, "sucesso", workflow_id=2, inicio="2024-10-01T11:00:00Z"),
    ])

    assert not marcar_flaky(linha_do_tempo(runs)).iloc[0]["flaky"]


def test_head_sha_nulo_ainda_e_agrupado():
    # groupby descarta chaves NaN por padrão: sem dropna=False estas falhas
    # nunca seriam marcadas e ninguém perceberia.
    runs = _df([
        _run(1, "falha", head_sha=None, inicio="2024-10-01T10:00:00Z"),
        _run(2, "sucesso", head_sha=None, inicio="2024-10-01T11:00:00Z"),
    ])

    assert marcar_flaky(linha_do_tempo(runs)).iloc[0]["flaky"]


def test_tentativa_recuperada_pelo_run_e_flaky():
    # O caso central: tentativa 1 falhou, o run (tentativa 2) passou.
    runs = _df([_run(1, "sucesso", run_attempt=2, inicio="2024-10-01T10:00:00Z")])
    attempts = _df([_tentativa(1, 1, inicio="2024-10-01T09:00:00Z")])

    marcado = marcar_flaky(linha_do_tempo(runs, attempts))

    tentativa = marcado[marcado["origem"] == "tentativa"].iloc[0]
    assert tentativa["flaky"]


def test_sem_sucesso_nenhum_nada_e_flaky():
    runs = _df([
        _run(1, "falha", inicio="2024-10-01T10:00:00Z"),
        _run(2, "falha", inicio="2024-10-01T11:00:00Z"),
    ])

    assert not marcar_flaky(linha_do_tempo(runs))["flaky"].any()
