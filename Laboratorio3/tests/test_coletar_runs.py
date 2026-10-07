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


# --- achados da revisão -------------------------------------------------

@responses.activate
@pytest.mark.parametrize("valor", [None, 0])
def test_run_attempt_nulo_ou_zero_vira_1(valor):
    # int(None) levanta TypeError e mataria a coleta do repositório inteiro.
    # Sem este caso, um refactor para .get("run_attempt", 1) passa despercebido.
    responses.get(URL, **_resposta(1, [_run(1, run_attempt=valor)]))

    linha = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31)).runs[0]

    assert linha["run_attempt"] == 1


@responses.activate
def test_sem_total_count_a_mensagem_explica_o_problema():
    # O KeyError incidental de carga["total_count"] também casaria com
    # match="total_count": é preciso afirmar a mensagem, não só o tipo.
    responses.get(URL, json={"workflow_runs": []}, status=200)

    with pytest.raises(KeyError, match="saturou"):
        coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))


@responses.activate
def test_run_fora_da_fatia_e_contado():
    # Se a API ignorar o created= em vez de recusá-lo, runs de fora da janela
    # entram em silêncio e enviesam a amostra inteira. Isso tem que gritar.
    responses.get(URL, **_resposta(2, [
        _run(1, created_at="2024-10-05T12:00:00Z"),
        _run(2, created_at="2023-01-01T12:00:00Z"),
    ]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert coleta.fora_da_fatia == 1
    assert len(coleta.runs) == 2, "contar não é descartar: o dado bruto fica"


@responses.activate
def test_created_at_ausente_nao_conta_como_fora():
    responses.get(URL, **_resposta(1, [_run(1, created_at=None)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert coleta.fora_da_fatia == 0, "sem data não dá para afirmar que está fora"


@responses.activate
def test_subdivisao_para_quando_o_filtro_nao_estreita():
    # Se a filha devolve o mesmo total que a mãe, o created= não está
    # mordendo: continuar dividindo gastaria milhares de chamadas à toa.
    responses.get(URL, **_resposta(5000, [_run(1)]))
    responses.get(URL, **_resposta(5000, [_run(2)]))
    responses.get(URL, **_resposta(5000, [_run(3)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert len(coleta.saturadas) == 2, "as duas metades inúteis viram diagnóstico"
    assert len(responses.calls) == 3, "parou na primeira divisão sem ganho"


@responses.activate
def test_403_nao_descarta_o_repositorio():
    # Um 403 no mês 12 não pode jogar fora os 11 meses já coletados.
    responses.get(URL, **_resposta(1, [_run(1)]))
    responses.get(URL, json={"message": "Resource not accessible"}, status=403)

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 11, 30))

    assert len(coleta.runs) == 1, "o mês que deu certo tem que sobreviver"
    assert len(coleta.saturadas) == 1


@responses.activate
def test_401_ainda_derruba_porque_e_erro_de_token():
    # Degradar aqui esconderia um token errado atrás de um CSV vazio.
    responses.get(URL, json={"message": "Bad credentials"}, status=401)

    with pytest.raises(Exception):
        coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))


@responses.activate
def test_workflow_id_ausente_e_erro_na_origem():
    # Com workflow_id nulo em algumas linhas o pandas coage a coluna para
    # float e o CSV sai com 7.0 — a #42 agrupa episódios por esse campo.
    item = _run(1)
    del item["workflow_id"]
    responses.get(URL, **_resposta(1, [item]))

    with pytest.raises(KeyError, match="workflow_id"):
        coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))


@responses.activate
def test_workflow_id_sai_inteiro_no_csv(tmp_path):
    responses.get(URL, **_resposta(2, [_run(1), _run(2)]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))
    destino = tmp_path / "runs.csv"
    df_runs(coleta.runs).to_csv(destino, index=False)

    assert "7.0" not in destino.read_text(encoding="utf-8")


@responses.activate
def test_403_na_segunda_pagina_tambem_degrada():
    # A página 1 vem do cache da sondagem, então um erro de paginação só pode
    # aparecer da página 2 em diante. É o ramo que o try do paginar cobre.
    p2 = f"{URL}?page=2"
    responses.get(URL, **_resposta(2, [_run(1)],
                                   headers={"Link": f'<{p2}>; rel="next"'}))
    responses.get(p2, json={"message": "Resource not accessible"}, status=403)

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert len(coleta.saturadas) == 1, "a fatia interrompida vira diagnóstico"
    assert coleta.runs == [], "a fatia não entrou, mas o repositório sobreviveu"


@responses.activate
def test_created_at_impossivel_de_ler_nao_conta_como_fora():
    responses.get(URL, **_resposta(1, [_run(1, created_at="ontem de manhã")]))

    coleta = coletar_runs(REPO, "main", date(2024, 10, 1), date(2024, 10, 31))

    assert coleta.fora_da_fatia == 0
