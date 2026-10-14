"""Quanto de cota cada endpoint custou, e quanto o cache economizou."""
import pandas as pd
import pytest
import responses

from coleta.cache import Cache
from coleta.http import (
    CAMINHO_CUSTO, Cliente, endpoint_de, escrever_custo_api,
)
from metricas.schemas import SCHEMAS, validar

RELEASES = "https://api.github.com/repos/torvalds/linux/releases"
SHA = "a" * 40


@pytest.fixture
def cliente(tmp_path):
    return Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                   agora=lambda: 1000.0, dormir=lambda s: None)


@pytest.mark.parametrize("url, esperado", [
    ("https://api.github.com/repos/torvalds/linux/releases",
     "/repos/{owner}/{repo}/releases"),
    ("https://api.github.com/repos/a/b/actions/runs?page=3&event=push",
     "/repos/{owner}/{repo}/actions/runs"),
    (f"https://api.github.com/repos/a/b/commits/{SHA}",
     "/repos/{owner}/{repo}/commits/{sha}"),
    ("https://api.github.com/repos/a/b/deployments/12345/statuses",
     "/repos/{owner}/{repo}/deployments/{id}/statuses"),
    ("https://api.github.com/repos/a/b/compare/v1...v2",
     "/repos/{owner}/{repo}/compare/{base}...{head}"),
    ("https://api.github.com/orgs/python", "/orgs/{org}"),
    ("https://api.github.com/users/torvalds", "/users/{user}"),
    ("https://api.github.com/search/repositories?q=stars:%3E1000",
     "/search/repositories"),
    ("https://api.github.com/rate_limit", "/rate_limit"),
])
def test_endpoint_vira_template(url, esperado):
    assert endpoint_de(url) == esperado


@responses.activate
def test_repositorios_diferentes_somam_no_mesmo_endpoint(cliente):
    # Sem normalizar, o CSV teria uma linha por repositório.
    responses.get(RELEASES, json=[], status=200)
    responses.get("https://api.github.com/repos/python/cpython/releases",
                  json=[], status=200)

    cliente.get(RELEASES)
    cliente.get("https://api.github.com/repos/python/cpython/releases")

    custo = cliente.custo()
    assert len(custo) == 1
    assert custo.iloc[0]["endpoint"] == "/repos/{owner}/{repo}/releases"
    assert custo.iloc[0]["chamadas"] == 2


@responses.activate
def test_acerto_de_cache_conta_em_do_cache(cliente):
    responses.get(RELEASES, json=[], status=200)

    cliente.get(RELEASES)
    cliente.get(RELEASES)
    cliente.get(RELEASES)

    linha = cliente.custo().iloc[0]
    assert linha["chamadas"] == 1
    assert linha["do_cache"] == 2


@responses.activate
def test_cada_tentativa_de_rede_conta_como_chamada(cliente):
    # Retry gasta cota de verdade, então aparece no custo.
    responses.get(RELEASES, json={"message": "Bad gateway"}, status=502)
    responses.get(RELEASES, json=[], status=200)

    cliente.get(RELEASES)

    assert cliente.custo().iloc[0]["chamadas"] == 2


@responses.activate
def test_paginas_somam_no_mesmo_endpoint(cliente):
    p2 = f"{RELEASES}?page=2"
    responses.get(RELEASES, json=[{"id": 1}], status=200,
                  headers={"Link": f'<{p2}>; rel="next"'})
    responses.get(p2, json=[{"id": 2}], status=200)

    cliente.paginar(RELEASES)

    custo = cliente.custo()
    assert len(custo) == 1
    assert custo.iloc[0]["chamadas"] == 2


def test_custo_vazio_respeita_o_contrato(cliente):
    validar(cliente.custo(), SCHEMAS["custo_api"])


@responses.activate
def test_custo_respeita_o_contrato(cliente):
    responses.get(RELEASES, json=[], status=200)
    cliente.get(RELEASES)

    custo = cliente.custo()

    validar(custo, SCHEMAS["custo_api"])
    assert list(custo.columns) == ["endpoint", "chamadas", "do_cache"]


@responses.activate
def test_custo_sai_ordenado_por_endpoint(cliente):
    responses.get(RELEASES, json=[], status=200)
    responses.get("https://api.github.com/repos/a/b/actions/runs",
                  json={"workflow_runs": []}, status=200)
    cliente.get(RELEASES)
    cliente.get("https://api.github.com/repos/a/b/actions/runs")

    endpoints = list(cliente.custo()["endpoint"])
    assert endpoints == sorted(endpoints)


@responses.activate
def test_escrever_gera_csv_valido(cliente, tmp_path):
    responses.get(RELEASES, json=[], status=200)
    cliente.get(RELEASES)
    destino = tmp_path / "saida" / "custo_api.csv"

    caminho = escrever_custo_api(destino, cliente=cliente)

    assert caminho == destino
    lido = pd.read_csv(destino)
    validar(lido, SCHEMAS["custo_api"])
    assert lido.iloc[0]["chamadas"] == 1


def test_caminho_padrao_fica_em_data_processed():
    assert CAMINHO_CUSTO == "data/processed/custo_api.csv"


@pytest.mark.parametrize("url, esperado", [
    # compare é o cavalo de batalha da B2: ~200 repos x >=5 releases. Sem
    # normalizar o intervalo, custo_api.csv ganha mil linhas e para de
    # responder onde a cota foi gasta, que é a razão de ele existir.
    ("https://api.github.com/repos/a/b/compare/v1.2.3...v1.2.4",
     "/repos/{owner}/{repo}/compare/{base}...{head}"),
    (f"https://api.github.com/repos/a/b/compare/{SHA}...{'b' * 40}",
     "/repos/{owner}/{repo}/compare/{base}...{head}"),
    ("https://api.github.com/repos/a/b/git/refs/tags/v1.0.0",
     "/repos/{owner}/{repo}/git/refs/tags/{tag}"),
    ("https://api.github.com/repos/a/b/releases/tags/v2.0.0",
     "/repos/{owner}/{repo}/releases/tags/{tag}"),
    # A listagem de tags é coleção, não recurso: nada a substituir.
    ("https://api.github.com/repos/a/b/tags", "/repos/{owner}/{repo}/tags"),
])
def test_endpoint_normaliza_intervalos_e_tags(url, esperado):
    assert endpoint_de(url) == esperado


@responses.activate
def test_compares_diferentes_somam_numa_linha_so(cliente):
    base = "https://api.github.com/repos/a/b/compare"
    for par in ("v1...v2", "v2...v3", "v3...v4"):
        responses.get(f"{base}/{par}", json={"commits": []}, status=200)
        cliente.get(f"{base}/{par}")

    custo = cliente.custo()
    assert len(custo) == 1, f"uma linha por compare: {list(custo['endpoint'])}"
    assert custo.iloc[0]["chamadas"] == 3


# --- custo acumulado entre execuções sobre o mesmo cache (Issue #66) ---------------

def _cliente_em(caminho):
    return Cliente(token="tok", cache=Cache(caminho),
                   agora=lambda: 1000.0, dormir=lambda s: None)


@responses.activate
def test_custo_acumula_entre_execucoes_que_retomam_o_mesmo_cache(tmp_path):
    responses.add(responses.GET, RELEASES, json=[])
    responses.add(responses.GET, f"{RELEASES}?page=2", json=[])
    cache = tmp_path / "c.sqlite"

    primeira = _cliente_em(cache)
    primeira.get(RELEASES)                    # 1 chamada de verdade
    escrever_custo_api(tmp_path / "a.csv", primeira)

    segunda = _cliente_em(cache)              # retomada: o mesmo cache em disco
    segunda.get(RELEASES)                     # servida pelo cache
    segunda.get(f"{RELEASES}?page=2")         # 1 chamada nova
    escrever_custo_api(tmp_path / "b.csv", segunda)

    df = pd.read_csv(tmp_path / "b.csv").set_index("endpoint")
    linha = df.loc["/repos/{owner}/{repo}/releases"]
    assert linha["chamadas"] == 2 and linha["do_cache"] == 1
    validar(pd.read_csv(tmp_path / "b.csv"), SCHEMAS["custo_api"])


@responses.activate
def test_escrever_duas_vezes_no_mesmo_processo_nao_conta_em_dobro(tmp_path):
    responses.add(responses.GET, RELEASES, json=[])
    c = _cliente_em(tmp_path / "c.sqlite")
    c.get(RELEASES)
    escrever_custo_api(tmp_path / "x.csv", c)
    escrever_custo_api(tmp_path / "x.csv", c)
    assert pd.read_csv(tmp_path / "x.csv")["chamadas"].sum() == 1


@responses.activate
def test_cache_novo_comeca_do_zero_e_ignora_csv_antigo_em_disco(tmp_path):
    # um replicador com cache vazio não pode herdar o custo de outra coleta
    (tmp_path / "custo.csv").write_text(
        "endpoint,chamadas,do_cache\n/repos/{owner}/{repo}/releases,9999,9999\n")
    responses.add(responses.GET, RELEASES, json=[])
    c = _cliente_em(tmp_path / "novo.sqlite")
    c.get(RELEASES)
    escrever_custo_api(tmp_path / "custo.csv", c)
    assert pd.read_csv(tmp_path / "custo.csv")["chamadas"].tolist() == [1]


def test_cache_guarda_o_custo_acumulado_depois_de_reabrir(tmp_path):
    cache = Cache(tmp_path / "c.sqlite")
    cache.somar_custo({"/x": (2, 1)})
    cache.somar_custo({"/x": (1, 0), "/y": (0, 4)})
    cache.fechar()
    assert Cache(tmp_path / "c.sqlite").custo_acumulado() == {
        "/x": (3, 1), "/y": (0, 4)}
