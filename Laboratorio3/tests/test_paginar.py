"""paginar(): segue Link rel="next" em listas e em objetos."""
import pytest
import responses

from coleta.cache import Cache
from coleta.http import Cliente, ErroDeHTTP

BASE = "https://api.github.com/repos/a/b/releases"


@pytest.fixture
def cliente(tmp_path):
    return Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                   agora=lambda: 1000.0, dormir=lambda s: None)


def _link(proxima: str) -> dict:
    return {"Link": f'<{proxima}>; rel="next", <{proxima}>; rel="last"'}


@responses.activate
def test_tres_paginas_devolvem_todos_os_itens(cliente):
    p2, p3 = f"{BASE}?page=2", f"{BASE}?page=3"
    responses.get(BASE, json=[{"id": 1}, {"id": 2}], status=200, headers=_link(p2))
    responses.get(p2, json=[{"id": 3}, {"id": 4}], status=200, headers=_link(p3))
    responses.get(p3, json=[{"id": 5}], status=200)

    itens = cliente.paginar(BASE)

    assert [i["id"] for i in itens] == [1, 2, 3, 4, 5]
    assert len(responses.calls) == 3


@responses.activate
def test_resposta_sem_link_para_na_primeira_pagina(cliente):
    responses.get(BASE, json=[{"id": 1}], status=200)

    assert cliente.paginar(BASE) == [{"id": 1}]
    assert len(responses.calls) == 1


@responses.activate
def test_link_sem_rel_next_para(cliente):
    # Só prev e last: não há próxima página. Seguir o last giraria para trás.
    responses.get(BASE, json=[{"id": 1}], status=200,
                  headers={"Link": f'<{BASE}?page=1>; rel="prev", '
                                   f'<{BASE}?page=9>; rel="last"'})

    assert cliente.paginar(BASE) == [{"id": 1}]
    assert len(responses.calls) == 1


@responses.activate
def test_objeto_com_workflow_runs(cliente):
    url = "https://api.github.com/repos/a/b/actions/runs"
    p2 = f"{url}?page=2"
    responses.get(url, json={"total_count": 3, "workflow_runs": [{"id": 1}, {"id": 2}]},
                  status=200, headers=_link(p2))
    responses.get(p2, json={"total_count": 3, "workflow_runs": [{"id": 3}]}, status=200)

    assert [i["id"] for i in cliente.paginar(url)] == [1, 2, 3]


@responses.activate
def test_objeto_com_items_da_busca(cliente):
    url = "https://api.github.com/search/repositories"
    responses.get(url, json={"total_count": 1, "items": [{"full_name": "a/b"}]}, status=200)

    assert cliente.paginar(url) == [{"full_name": "a/b"}]


@responses.activate
def test_objeto_com_commits_do_compare(cliente):
    url = "https://api.github.com/repos/a/b/compare/v1...v2"
    responses.get(url, json={"status": "ahead", "total_commits": 2,
                             "commits": [{"sha": "aa"}, {"sha": "bb"}]}, status=200)

    assert [c["sha"] for c in cliente.paginar(url)] == ["aa", "bb"]


@responses.activate
def test_objeto_sem_lista_conhecida_diz_quais_chaves_vieram(cliente):
    responses.get(BASE, json={"message": "algo", "documentation_url": "x"}, status=200)

    with pytest.raises(ErroDeHTTP) as erro:
        cliente.paginar(BASE)

    assert "documentation_url" in str(erro.value)
    assert "message" in str(erro.value)


@responses.activate
def test_primeira_pagina_pede_per_page_100(cliente):
    # O padrão da API é 30; 100 corta as chamadas em três.
    responses.get(BASE, json=[], status=200)

    cliente.paginar(BASE)

    assert "per_page=100" in responses.calls[0].request.url


@responses.activate
def test_per_page_do_chamador_tem_precedencia(cliente):
    responses.get(BASE, json=[], status=200)

    cliente.paginar(BASE, {"per_page": 5})

    assert "per_page=5" in responses.calls[0].request.url


@responses.activate
def test_paginas_seguintes_nao_reenviam_params(cliente):
    # A URL do rel="next" já traz tudo. Reenviar params duplicaria a query.
    p2 = f"{BASE}?page=2&per_page=100"
    responses.get(BASE, json=[{"id": 1}], status=200, headers=_link(p2))
    responses.get(p2, json=[{"id": 2}], status=200)

    cliente.paginar(BASE, {"event": "push"})

    segunda = responses.calls[1].request.url
    assert segunda == p2, f"a segunda chamada ganhou parâmetros a mais: {segunda}"


@responses.activate
def test_cada_pagina_e_cacheada_pela_propria_url(cliente):
    # É isto que faz a retomada funcionar no meio de uma paginação longa.
    p2 = f"{BASE}?page=2"
    responses.get(BASE, json=[{"id": 1}], status=200, headers=_link(p2))
    responses.get(p2, json=[{"id": 2}], status=200)

    primeira = cliente.paginar(BASE)
    segunda = cliente.paginar(BASE)

    assert primeira == segunda
    assert len(responses.calls) == 2, "a segunda paginação foi toda do cache"


@responses.activate
def test_next_que_aponta_para_si_mesmo_nao_vira_laco(cliente):
    responses.get(BASE, json=[{"id": 1}], status=200, headers=_link(BASE))

    assert cliente.paginar(BASE) == [{"id": 1}]
    assert len(responses.calls) == 1


@responses.activate
def test_404_ao_paginar_levanta_com_status(cliente):
    # Quem quiser tratar o 404 (compare quebrado) usa get, não paginar.
    responses.get(BASE, json={"message": "Not Found"}, status=404)

    with pytest.raises(ErroDeHTTP) as erro:
        cliente.paginar(BASE)

    assert erro.value.status == 404
