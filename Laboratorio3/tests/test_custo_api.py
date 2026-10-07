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
     "/repos/{owner}/{repo}/compare/v1...v2"),
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
