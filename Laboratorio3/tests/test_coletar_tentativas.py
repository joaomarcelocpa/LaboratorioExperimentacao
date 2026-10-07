"""Tentativas anteriores: a listagem de runs só mostra a última."""
import pytest
import responses

from coleta.cache import Cache
from coleta.http import Cliente, redefinir_cliente
from coleta.runs import (
    MAX_TENTATIVAS_PADRAO, coletar_tentativas, df_tentativas,
    esquecer_tentativas_podadas, tentativas_podadas,
)
from metricas.schemas import SCHEMAS, validar

REPO = "torvalds/linux"
BASE = f"https://api.github.com/repos/{REPO}/actions/runs"


@pytest.fixture(autouse=True)
def ambiente(tmp_path):
    redefinir_cliente(Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                              agora=lambda: 1000.0, dormir=lambda s: None))
    esquecer_tentativas_podadas()
    yield
    redefinir_cliente(None)
    esquecer_tentativas_podadas()


def _linha_de_run(run_id, run_attempt):
    return {"repo": REPO, "run_id": run_id, "run_attempt": run_attempt}


def _tentativa(k, conclusion="failure"):
    # As datas são fixas de propósito: o que varia é o número da tentativa, e
    # interpolar k na hora produziria ISO inválido para k > 23.
    return {
        "run_attempt": k,
        "conclusion": conclusion,
        "run_started_at": "2024-10-01T01:00:00Z",
        "updated_at": "2024-10-01T01:30:00Z",
    }


def _tentativas_pedidas() -> list[int]:
    return [int(c.request.url.rsplit("/", 1)[-1]) for c in responses.calls]


@responses.activate
def test_run_com_tres_tentativas_busca_as_duas_anteriores():
    responses.get(f"{BASE}/1/attempts/1", json=_tentativa(1), status=200)
    responses.get(f"{BASE}/1/attempts/2", json=_tentativa(2), status=200)

    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 3)])

    assert [l["tentativa"] for l in linhas] == [1, 2]
    assert len(responses.calls) == 2


@responses.activate
def test_run_de_tentativa_unica_nao_faz_chamada():
    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 1)])

    assert linhas == []
    assert len(responses.calls) == 0


@responses.activate
def test_run_sem_run_attempt_nao_faz_chamada():
    linhas = coletar_tentativas(REPO, [{"repo": REPO, "run_id": 1}])

    assert linhas == []
    assert len(responses.calls) == 0


@responses.activate
def test_campos_seguem_o_contrato():
    responses.get(f"{BASE}/9/attempts/1", json=_tentativa(1, "timed_out"), status=200)

    linha = coletar_tentativas(REPO, [_linha_de_run(9, 2)])[0]

    assert linha == {
        "repo": REPO,
        "run_id": 9,
        "tentativa": 1,
        "conclusion": "timed_out",
        "inicio": "2024-10-01T01:00:00Z",
        "fim": "2024-10-01T01:30:00Z",
    }


@responses.activate
def test_teto_corta_e_mantem_as_mais_recentes():
    # Para run_attempt=40 com teto 5, as úteis são as tentativas 35 a 39: é o
    # rerun imediatamente anterior que diz se a falha foi flaky.
    for k in range(35, 40):
        responses.get(f"{BASE}/1/attempts/{k}", json=_tentativa(k), status=200)

    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 40)], max_tentativas=5)

    assert _tentativas_pedidas() == [35, 36, 37, 38, 39]
    assert [l["tentativa"] for l in linhas] == [35, 36, 37, 38, 39]


@responses.activate
def test_teto_que_nao_corta_busca_todas():
    responses.get(f"{BASE}/1/attempts/1", json=_tentativa(1), status=200)
    responses.get(f"{BASE}/1/attempts/2", json=_tentativa(2), status=200)

    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 3)], max_tentativas=5)

    assert len(linhas) == 2
    assert tentativas_podadas()["cortadas_pelo_teto"] == 0


@responses.activate
def test_corte_pelo_teto_e_contado():
    for k in range(35, 40):
        responses.get(f"{BASE}/1/attempts/{k}", json=_tentativa(k), status=200)

    coletar_tentativas(REPO, [_linha_de_run(1, 40)], max_tentativas=5)

    # 39 tentativas anteriores existiam; 5 foram buscadas.
    assert tentativas_podadas()["cortadas_pelo_teto"] == 34


@responses.activate
def test_404_numa_tentativa_e_contado_e_ignorado():
    # O GitHub poda tentativas antigas. Isso não pode derrubar o repositório.
    responses.get(f"{BASE}/1/attempts/1", json={"message": "Not Found"}, status=404)
    responses.get(f"{BASE}/1/attempts/2", json=_tentativa(2), status=200)

    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 3)])

    assert [l["tentativa"] for l in linhas] == [2]
    assert tentativas_podadas()["ausentes_na_api"] == 1


@responses.activate
def test_varios_runs_de_uma_vez():
    responses.get(f"{BASE}/1/attempts/1", json=_tentativa(1), status=200)
    responses.get(f"{BASE}/2/attempts/1", json=_tentativa(1), status=200)

    linhas = coletar_tentativas(REPO, [_linha_de_run(1, 2), _linha_de_run(2, 2)])

    assert sorted(l["run_id"] for l in linhas) == [1, 2]


@responses.activate
def test_df_tentativas_respeita_o_contrato():
    responses.get(f"{BASE}/1/attempts/1", json=_tentativa(1), status=200)

    df = df_tentativas(coletar_tentativas(REPO, [_linha_de_run(1, 2)]))

    validar(df, SCHEMAS["run_attempts"])
    assert list(df.columns) == list(SCHEMAS["run_attempts"].colunas)


def test_df_tentativas_vazio_respeita_o_contrato():
    df = df_tentativas([])

    validar(df, SCHEMAS["run_attempts"])
    assert df.empty


def test_padrao_do_teto_e_cinco():
    assert MAX_TENTATIVAS_PADRAO == 5
