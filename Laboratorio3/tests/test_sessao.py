import pytest
import requests
import responses

from coleta import http
from coleta.cache import Cache
from coleta.sessao import SessaoHttp


@pytest.fixture(autouse=True)
def cliente(tmp_path):
    c = http.Cliente(token="t", cache=Cache(tmp_path / "c.sqlite"), dormir=lambda s: None)
    http.redefinir_cliente(c)
    yield c
    http.redefinir_cliente(None)


@responses.activate
def test_segunda_chamada_nao_sai_da_maquina():
    responses.add(responses.GET, "https://api.github.com/repos/o/r/releases", json=[{"a": 1}])
    s = SessaoHttp()
    assert s.get("https://api.github.com/repos/o/r/releases").json() == [{"a": 1}]
    assert s.get("https://api.github.com/repos/o/r/releases").json() == [{"a": 1}]
    assert len(responses.calls) == 1


@responses.activate
def test_404_nao_levanta_e_expoe_status_code():
    responses.add(responses.GET, "https://api.github.com/x", status=404, json={})
    r = SessaoHttp().get("https://api.github.com/x")
    assert r.status_code == 404


@responses.activate
def test_raise_for_status_em_erro_e_headers_sem_caixa():
    responses.add(responses.GET, "https://api.github.com/x", status=404, json={},
                  headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'})
    r = SessaoHttp().get("https://api.github.com/x")
    assert 'rel="next"' in r.headers.get("link")
    assert 'rel="next"' in r.headers.get("Link")
    with pytest.raises(requests.HTTPError):
        r.raise_for_status()


@responses.activate
def test_releases_e_tags_pedem_pagina_de_100_como_o_filtro():
    for caminho in ("releases", "tags"):
        responses.add(responses.GET, f"https://api.github.com/repos/o/r/{caminho}", json=[])
        SessaoHttp().get(f"https://api.github.com/repos/o/r/{caminho}")
    assert all("per_page=100" in c.request.url for c in responses.calls)


@responses.activate
def test_releases_reaproveita_o_cache_do_paginar():
    url = "https://api.github.com/repos/o/r/releases"
    responses.add(responses.GET, url, json=[{"id": 1}])
    http.paginar(url)
    SessaoHttp().get(url)
    assert len(responses.calls) == 1


@responses.activate
def test_compare_nao_ganha_per_page():
    url = "https://api.github.com/repos/o/r/compare/v1...v2"
    responses.add(responses.GET, url, json={"commits": []})
    SessaoHttp().get(url)
    assert "per_page" not in responses.calls[0].request.url
