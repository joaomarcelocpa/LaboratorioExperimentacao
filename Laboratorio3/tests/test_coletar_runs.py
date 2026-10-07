"""Coleta de runs: saturação, subdivisão, dedup e contrato."""
from datetime import date

import pandas as pd
import pytest
import responses

from coleta.cache import Cache
from coleta.http import Cliente, redefinir_cliente
from coleta.runs import (
    CAMINHO_FATIAS, coletar_runs, df_runs, escrever_fatias_saturadas,
)
from metricas.schemas import SCHEMAS, validar

REPO = "torvalds/linux"
URL = f"https://api.github.com/repos/{REPO}/actions/runs"


@pytest.fixture(autouse=True)
def cliente_sem_rede(tmp_path):
    """Todo get/paginar do módulo passa por um cliente fake, sem disco real."""
    redefinir_cliente(Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                              agora=lambda: 1000.0, dormir=lambda s: None))
    yield
    redefinir_cliente(None)


def _run(run_id, **extra):
    base = {
        "id": run_id,
        "workflow_id": 7,
        "name": "CI",
        "path": ".github/workflows/ci.yml",
        "event": "push",
        "head_sha": "a" * 40,
        "run_attempt": 1,
        "conclusion": "success",
        "run_started_at": "2024-10-01T10:00:00Z",
        "updated_at": "2024-10-01T10:20:00Z",
        "created_at": "2024-10-01T09:59:00Z",
    }
    base.update(extra)
    return base


def _resposta(total, runs, **kwargs):
    return dict(json={"total_count": total, "workflow_runs": runs},
                status=200, **kwargs)


def _created_de(url: str) -> str:
    """O valor do created= de uma URL pedida, já decodificado."""
    from urllib.parse import parse_qs, unquote, urlsplit
    return unquote(parse_qs(urlsplit(url).query)["created"][0])


# --- caminho feliz ------------------------------------------------------

@responses.activate
def test_um_mes_com_runs():
    responses.get(URL, **_resposta(2, [_run(1), _run(2)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert [r["run_id"] for r in coleta.runs] == [1, 2]
    assert coleta.saturadas == []


@responses.activate
def test_mes_sem_runs_nao_quebra():
    # Critério de aceite da Issue.
    responses.get(URL, **_resposta(0, []))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert coleta.runs == []
    assert coleta.saturadas == []


@responses.activate
def test_manda_branch_e_event_push():
    responses.get(URL, **_resposta(0, []))

    coletar_runs(REPO, "develop", date(2024, 10, 1), date(2024, 10, 31))

    pedido = responses.calls[0].request.url
    assert "branch=develop" in pedido
    assert "event=push" in pedido
    assert _created_de(pedido) == "2024-10-01..2024-10-31"


@responses.activate
def test_campos_seguem_o_contrato_e_nao_a_api():
    responses.get(URL, **_resposta(1, [_run(1, conclusion="timed_out")]))

    linha = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31)).runs[0]

    assert linha["run_id"] == 1
    assert linha["workflow_nome"] == "CI"
    assert linha["inicio"] == "2024-10-01T10:00:00Z"
    assert linha["fim"] == "2024-10-01T10:20:00Z"
    assert linha["criado_em"] == "2024-10-01T09:59:00Z"
    assert linha["classe"] == "falha"
    assert "path" not in linha, "path não entra no contrato de runs.csv"
    assert "id" not in linha and "name" not in linha


# --- saturação e subdivisão ---------------------------------------------

@responses.activate
def test_mes_no_teto_de_1000_e_subdividido():
    # Critério de aceite da Issue. O mês satura; as duas quinzenas não.
    responses.get(URL, **_resposta(1000, [_run(1)]))
    responses.get(URL, **_resposta(3, [_run(10), _run(11)]))
    responses.get(URL, **_resposta(3, [_run(12)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert sorted(r["run_id"] for r in coleta.runs) == [10, 11, 12]
    assert coleta.saturadas == [], "as quinzenas couberam, nada a registrar"
    # Três sondagens: o mês que saturou e as duas metades que couberam.
    assert len(responses.calls) == 3
    intervalos = {_created_de(c.request.url) for c in responses.calls}
    assert len(intervalos) == 3, f"as fatias não foram distintas: {intervalos}"


@responses.activate
def test_fatia_saturada_no_piso_e_registrada():
    # Uma hora com 1.000 runs: não dá para subdividir mais. Vira diagnóstico
    # em vez de sumir em silêncio.
    for _ in range(200):
        responses.get(URL, **_resposta(1000, [_run(1)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 1))

    assert coleta.saturadas, "nenhuma fatia saturada registrada"
    assert all(f.repo == REPO for f in coleta.saturadas)
    assert all(f.total_count >= 1000 for f in coleta.saturadas)


@responses.activate
def test_422_na_forma_com_hora_vira_diagnostico_e_nao_derruba():
    # Se a API recusar created= com hora, a recursão para ali.
    responses.get(URL, **_resposta(1000, [_run(1)]))     # o dia satura
    responses.get(URL, json={"message": "Invalid"}, status=422)
    responses.get(URL, json={"message": "Invalid"}, status=422)

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 1))

    assert coleta.saturadas, "a fatia recusada deveria virar diagnóstico"


@responses.activate
def test_dedup_por_run_id():
    # Fatias são disjuntas, mas uma linha repetida deslocaria o CFR e
    # inventaria episódios de falha na RQ 04.
    responses.get(URL, **_resposta(1000, [_run(1)]))
    responses.get(URL, **_resposta(2, [_run(5), _run(5)]))
    responses.get(URL, **_resposta(2, [_run(5)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert [r["run_id"] for r in coleta.runs] == [5]


# --- entradas tortas ----------------------------------------------------

@responses.activate
def test_resposta_sem_total_count_e_erro_explicito():
    # Um .get("total_count", 0) silencioso faria o repositório sair com zero
    # runs sem ninguém notar.
    responses.get(URL, json={"workflow_runs": []}, status=200)

    with pytest.raises(KeyError, match="total_count"):
        coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))


@responses.activate
def test_run_sem_run_attempt_vira_1():
    item = _run(1)
    del item["run_attempt"]
    responses.get(URL, **_resposta(1, [item]))

    linha = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31)).runs[0]

    assert linha["run_attempt"] == 1


@responses.activate
def test_run_em_andamento_sem_datas_nao_quebra():
    # conclusion vazio e datas nulas: o run ainda está rodando.
    responses.get(URL, **_resposta(1, [
        _run(1, conclusion=None, run_started_at=None, updated_at=None)
    ]))

    linha = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31)).runs[0]

    assert linha["classe"] == "ignorado"
    assert linha["inicio"] is None
    assert linha["fim"] is None


# --- contrato -----------------------------------------------------------

@responses.activate
def test_df_runs_respeita_o_contrato():
    responses.get(URL, **_resposta(2, [_run(1), _run(2, conclusion="failure")]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))
    df = df_runs(coleta.runs)

    validar(df, SCHEMAS["runs"])
    assert list(df.columns) == list(SCHEMAS["runs"].colunas)


def test_df_runs_vazio_respeita_o_contrato():
    df = df_runs([])

    validar(df, SCHEMAS["runs"])
    assert df.empty


# --- diagnóstico --------------------------------------------------------

def test_escrever_fatias_saturadas(tmp_path):
    from coleta.runs import FatiaSaturada

    destino = tmp_path / "saida" / "fatias_saturadas.csv"
    caminho = escrever_fatias_saturadas(
        [FatiaSaturada(REPO, "2024-10-01T00:00:00Z", "2024-10-01T00:59:59Z", 1000)],
        destino,
    )

    assert caminho == destino
    lido = pd.read_csv(destino)
    assert list(lido.columns) == ["repo", "inicio", "fim", "total_count"]
    assert lido.iloc[0]["total_count"] == 1000


def test_caminho_das_fatias_fica_em_data_processed():
    assert CAMINHO_FATIAS == "data/processed/fatias_saturadas.csv"
