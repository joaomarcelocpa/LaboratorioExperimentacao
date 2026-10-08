"""Deployments via GraphQL: paginação, estados, ambientes e reserva REST."""
import json
from datetime import date

import pytest
import requests
import responses

from coleta import deployments_graphql as dg
from coleta.cache import Cache
from coleta.deployments import coletar_deployments
from coleta.http import Cliente, ErroDeHTTP, redefinir_cliente
from coleta.sessao import SessaoHttp
from pipeline.config import Config

GQL = "https://api.github.com/graphql"
API = "https://api.github.com"


@pytest.fixture(autouse=True)
def cliente_sem_rede(tmp_path):
    redefinir_cliente(Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                              agora=lambda: 1000.0, dormir=lambda s: None))
    yield
    redefinir_cliente(None)


def _cfg(ambientes=("production", "prod")):
    return Config(
        janela_inicio=date(2024, 1, 1), janela_fim=date(2024, 12, 31),
        faixas_estrelas=[], min_releases=5, min_runs=50, n_repos=10, seed=1,
        ambientes_producao=list(ambientes), labels_bug=["bug"], n_dias_issue=7,
        bots=[], _janela_placeholder=False,
    )


def _no(id_, estado="SUCCESS", env="production", sha="a" * 40):
    return {"databaseId": id_, "environment": env,
            "createdAt": "2024-06-01T10:00:00Z", "commit": {"oid": sha},
            "latestStatus": {"state": estado} if estado else None}


def _pagina(nos, proxima=None):
    return {"data": {"repository": {"deployments": {
        "pageInfo": {"hasNextPage": proxima is not None, "endCursor": proxima},
        "nodes": nos}}}}


@responses.activate
def test_linhas_no_formato_de_deployments_csv():
    responses.add(responses.POST, GQL, json=_pagina([_no(7, "SUCCESS", sha="b" * 40)]))
    assert dg.deployments_com_estado("org/repo", ["production"]) == [{
        "repo": "org/repo", "id": 7, "environment": "production",
        "criado_em": "2024-06-01T10:00:00Z", "sha": "b" * 40,
        "estado_final": "success",
    }]


@responses.activate
def test_estado_em_minusculas_como_na_rest():
    responses.add(responses.POST, GQL, json=_pagina([
        _no(1, "FAILURE"), _no(2, "IN_PROGRESS"), _no(3, "ERROR")]))
    estados = [l["estado_final"] for l in dg.deployments_com_estado("o/r", ["production"])]
    assert estados == ["failure", "in_progress", "error"]


@responses.activate
def test_sem_status_e_desconhecido():
    responses.add(responses.POST, GQL, json=_pagina([_no(1, estado=None)]))
    assert dg.deployments_com_estado("o/r", ["production"])[0]["estado_final"] == "desconhecido"


@responses.activate
def test_envia_os_ambientes_do_config():
    responses.add(responses.POST, GQL, json=_pagina([]))
    dg.deployments_com_estado("o/r", ["production", "prod"])
    variaveis = json.loads(responses.calls[0].request.body)["variables"]
    assert variaveis["ambientes"] == ["production", "prod"]
    assert (variaveis["dono"], variaveis["nome"]) == ("o", "r")


@responses.activate
def test_segue_o_cursor_ate_acabar():
    responses.add(responses.POST, GQL, json=_pagina([_no(1)], proxima="C1"))
    responses.add(responses.POST, GQL, json=_pagina([_no(2)]))
    assert [l["id"] for l in dg.deployments_com_estado("o/r", ["production"])] == [1, 2]
    assert json.loads(responses.calls[1].request.body)["variables"]["depois"] == "C1"


def test_sem_ambientes_nao_gasta_chamada():
    assert dg.deployments_com_estado("o/r", []) == []


@responses.activate
def test_repositorio_nao_achado_devolve_none():
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "NOT_FOUND", "message": "x"}]})
    assert dg.deployments_com_estado("velho/nome", ["production"]) is None


@responses.activate
def test_outro_erro_estoura_em_vez_de_lista_parcial():
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "RATE_LIMITED", "message": "rate limit"}]})
    with pytest.raises(ErroDeHTTP, match="rate limit"):
        dg.deployments_com_estado("o/r", ["production"])


@responses.activate
def test_erro_parcial_com_dados_tambem_estoura():
    corpo = _pagina([_no(1)])
    corpo["errors"] = [{"type": "SERVICE_UNAVAILABLE", "message": "no meio"}]
    responses.add(responses.POST, GQL, json=corpo)
    with pytest.raises(ErroDeHTTP, match="no meio"):
        dg.deployments_com_estado("o/r", ["production"])


# --- integração com coletar_deployments --------------------------------------

@responses.activate
def test_sessao_do_pipeline_nao_faz_chamada_por_deployment():
    responses.add(responses.POST, GQL, json=_pagina(
        [_no(i) for i in range(100)], proxima="C"))
    responses.add(responses.POST, GQL, json=_pagina([_no(i) for i in range(100, 146)]))

    df = coletar_deployments("org/repo", _cfg(), SessaoHttp())

    assert len(df) == 146
    urls = [c.request.url for c in responses.calls]
    assert all(u == GQL for u in urls) and len(urls) == 2   # 146 deployments, 2 chamadas


@responses.activate
def test_repo_sem_deployments_de_producao_da_df_vazio():
    responses.add(responses.POST, GQL, json=_pagina([]))
    assert coletar_deployments("org/repo", _cfg(), SessaoHttp()).empty


@responses.activate
def test_renomeado_cai_no_caminho_rest():
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "NOT_FOUND", "message": "x"}]})
    responses.add(responses.GET, f"{API}/repos/org/repo/environments",
                  json={"environments": [{"name": "production"}]})
    responses.add(responses.GET, f"{API}/repos/org/repo/deployments",
                  json=[{"id": 5, "environment": "production",
                         "created_at": "2024-06-01T10:00:00Z", "sha": "abc"}],
                  headers={"Link": ""})
    responses.add(responses.GET, f"{API}/repos/org/repo/deployments/5/statuses",
                  json=[{"state": "success"}])
    df = coletar_deployments("org/repo", _cfg(), SessaoHttp())
    assert df.iloc[0]["id"] == 5 and df.iloc[0]["estado_final"] == "success"


@responses.activate
def test_sessao_sem_graphql_continua_no_rest():
    responses.add(responses.GET, f"{API}/repos/org/repo/environments",
                  json={"environments": []})
    assert coletar_deployments("org/repo", _cfg(), requests.Session()).empty
