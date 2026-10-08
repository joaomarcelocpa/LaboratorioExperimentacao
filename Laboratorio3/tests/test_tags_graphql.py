"""Tags via GraphQL: cliente, paginação, tags anotadas e reserva REST."""
import json
from datetime import date

import pytest
import requests
import responses

from coleta import http, tags
from coleta.cache import Cache
from coleta.http import Cliente, ErroDeHTTP, redefinir_cliente
from coleta.releases import coletar_releases
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


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1), janela_fim=date(2024, 12, 31),
        faixas_estrelas=[], min_releases=5, min_runs=50, n_repos=10, seed=1,
        ambientes_producao=[], labels_bug=["bug"], n_dias_issue=7, bots=[],
        _janela_placeholder=False,
    )


def _no(nome, oid="a" * 40, data="2024-03-01T10:00:00Z"):
    return {"name": nome,
            "target": {"__typename": "Commit", "oid": oid, "authoredDate": data}}


def _pagina(nos, proxima=None):
    return {"data": {"repository": {"refs": {
        "pageInfo": {"hasNextPage": proxima is not None, "endCursor": proxima},
        "nodes": nos}}}}


# --- cliente ---------------------------------------------------------------

@responses.activate
def test_graphql_e_um_post_com_token_e_corpo():
    responses.add(responses.POST, GQL, json={"data": {"x": 1}})
    r = http.graphql("query { x }", {"a": 1})
    assert r == {"data": {"x": 1}}
    req = responses.calls[0].request
    assert req.headers["Authorization"] == "Bearer tok"
    assert json.loads(req.body) == {"query": "query { x }", "variables": {"a": 1}}


@responses.activate
def test_graphql_repetido_vem_do_cache_e_conta_como_tal():
    responses.add(responses.POST, GQL, json={"data": {"x": 1}})
    http.graphql("query { x }", {"a": 1})
    http.graphql("query { x }", {"a": 1})
    assert len(responses.calls) == 1
    custo = http.cliente_padrao().custo().set_index("endpoint")
    assert custo.loc["/graphql", "chamadas"] == 1
    assert custo.loc["/graphql", "do_cache"] == 1


@responses.activate
def test_variaveis_diferentes_nao_colidem_no_cache():
    responses.add(responses.POST, GQL, json={"data": {"x": 1}})
    http.graphql("query { x }", {"a": 1})
    http.graphql("query { x }", {"a": 2})
    assert len(responses.calls) == 2


@responses.activate
def test_resposta_com_errors_nao_e_cacheada():
    responses.add(responses.POST, GQL, json={"errors": [{"message": "boom"}]})
    responses.add(responses.POST, GQL, json={"data": {"x": 1}})
    assert "errors" in http.graphql("query { x }")
    assert http.graphql("query { x }") == {"data": {"x": 1}}
    assert len(responses.calls) == 2   # o erro não envenenou o cache


@responses.activate
def test_status_nao_200_estoura():
    responses.add(responses.POST, GQL, status=401, json={"message": "Bad credentials"})
    with pytest.raises(ErroDeHTTP) as e:
        http.graphql("query { x }")
    assert e.value.status == 401


@responses.activate
def test_resposta_que_nao_e_json_estoura():
    responses.add(responses.POST, GQL, body="<html>", status=200)
    with pytest.raises(ErroDeHTTP, match="JSON"):
        http.graphql("query { x }")


@responses.activate
def test_graphql_5xx_repete_com_backoff():
    responses.add(responses.POST, GQL, status=502, body="bad gateway")
    responses.add(responses.POST, GQL, json={"data": {"x": 1}})
    assert http.graphql("query { x }") == {"data": {"x": 1}}
    assert len(responses.calls) == 2


def test_graphql_tem_balde_de_cota_proprio():
    assert http._recurso_de(GQL) == "graphql"
    assert http._recurso_de(f"{API}/search/repositories") == "search"
    assert http._recurso_de(f"{API}/repos/a/b") == "core"


# --- tags ------------------------------------------------------------------

@responses.activate
def test_tags_de_uma_pagina():
    responses.add(responses.POST, GQL, json=_pagina([
        _no("v1", "1" * 40, "2024-01-05T00:00:00Z"), _no("v2", "2" * 40)]))
    linhas = tags.tags_com_data("org/repo")
    assert linhas == [
        {"repo": "org/repo", "tag": "v1", "sha": "1" * 40,
         "data_commit": "2024-01-05T00:00:00Z"},
        {"repo": "org/repo", "tag": "v2", "sha": "2" * 40,
         "data_commit": "2024-03-01T10:00:00Z"},
    ]
    assert len(responses.calls) == 1


@responses.activate
def test_segue_o_cursor_ate_acabar():
    responses.add(responses.POST, GQL, json=_pagina([_no("v1")], proxima="CUR1"))
    responses.add(responses.POST, GQL, json=_pagina([_no("v2")]))
    assert [l["tag"] for l in tags.tags_com_data("org/repo")] == ["v1", "v2"]
    segunda = json.loads(responses.calls[1].request.body)["variables"]
    assert segunda["depois"] == "CUR1"


@responses.activate
def test_tag_anotada_desce_ate_o_commit():
    anotada = {"name": "v3", "target": {
        "__typename": "Tag", "target": {
            "__typename": "Commit", "oid": "c" * 40,
            "authoredDate": "2024-05-05T00:00:00Z"}}}
    responses.add(responses.POST, GQL, json=_pagina([anotada]))
    linha = tags.tags_com_data("org/repo")[0]
    assert linha["sha"] == "c" * 40 and linha["data_commit"] == "2024-05-05T00:00:00Z"


@responses.activate
def test_tag_que_nao_aponta_para_commit_e_ignorada(caplog):
    arvore = {"name": "v4", "target": {"__typename": "Tree"}}
    responses.add(responses.POST, GQL, json=_pagina([arvore, _no("v5")]))
    assert [l["tag"] for l in tags.tags_com_data("org/repo")] == ["v5"]
    assert "v4" in caplog.text


@responses.activate
def test_repositorio_nao_achado_devolve_none_para_cair_na_rest():
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "NOT_FOUND", "message": "Could not resolve"}]})
    assert tags.tags_com_data("velho/nome") is None


@responses.activate
def test_outro_erro_do_graphql_estoura_em_vez_de_lista_parcial():
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}]})
    with pytest.raises(ErroDeHTTP, match="rate limit"):
        tags.tags_com_data("org/repo")


@responses.activate
def test_erro_parcial_com_dados_tambem_estoura():
    corpo = _pagina([_no("v1")])
    corpo["errors"] = [{"type": "SERVICE_UNAVAILABLE", "message": "falhou no meio"}]
    responses.add(responses.POST, GQL, json=corpo)
    with pytest.raises(ErroDeHTTP, match="falhou no meio"):
        tags.tags_com_data("org/repo")


@responses.activate
def test_repo_sem_tags():
    responses.add(responses.POST, GQL, json=_pagina([]))
    assert tags.tags_com_data("org/repo") == []


# --- integração com coletar_releases ----------------------------------------

def _releases_vazias():
    responses.add(responses.GET, f"{API}/repos/org/repo/releases",
                  json=[], headers={"Link": ""})


@responses.activate
def test_sessao_do_pipeline_usa_graphql_e_nao_faz_chamada_por_tag():
    _releases_vazias()
    responses.add(responses.POST, GQL, json=_pagina(
        [_no(f"v{i}", f"{i:040d}") for i in range(100)], proxima="C")
    )
    responses.add(responses.POST, GQL, json=_pagina(
        [_no(f"w{i}", f"{i + 100:040d}") for i in range(20)]))

    _, tags_df = coletar_releases("org/repo", _cfg(), SessaoHttp())

    assert len(tags_df) == 120
    assert tags_df.columns.tolist() == ["repo", "tag", "sha", "data_commit"]
    urls = [c.request.url for c in responses.calls]
    assert not any("/commits/" in u for u in urls)
    assert sum(u == GQL for u in urls) == 2    # 120 tags, 2 chamadas


@responses.activate
def test_renomeado_cai_no_caminho_rest():
    _releases_vazias()
    responses.add(responses.POST, GQL, json={
        "data": {"repository": None},
        "errors": [{"type": "NOT_FOUND", "message": "x"}]})
    responses.add(responses.GET, f"{API}/repos/org/repo/tags",
                  json=[{"name": "v1", "commit": {"sha": "abc"}}], headers={"Link": ""})
    responses.add(responses.GET, f"{API}/repos/org/repo/commits/abc",
                  json={"commit": {"author": {"date": "2024-02-02T00:00:00Z"}}})

    _, tags_df = coletar_releases("org/repo", _cfg(), SessaoHttp())
    assert tags_df.iloc[0]["data_commit"] == "2024-02-02T00:00:00Z"


@responses.activate
def test_sessao_sem_graphql_continua_no_rest():
    _releases_vazias()
    responses.add(responses.GET, f"{API}/repos/org/repo/tags",
                  json=[{"name": "v1", "commit": {"sha": "abc"}}], headers={"Link": ""})
    responses.add(responses.GET, f"{API}/repos/org/repo/commits/abc",
                  json={"commit": {"author": {"date": "2024-02-02T00:00:00Z"}}})
    _, tags_df = coletar_releases("org/repo", _cfg(), requests.Session())
    assert tags_df.iloc[0]["sha"] == "abc"
