"""Cota e erros temporários. Nenhum teste dorme de verdade."""
import pytest
import requests
import responses

from coleta.cache import Cache, chave_de
from coleta.http import ESPERA_PADRAO_S, ESPERAS_5XX, Cliente, ErroDeHTTP

URL = "https://api.github.com/repos/a/b/releases"
OUTRA = "https://api.github.com/repos/a/b/tags"
AGORA = 1000.0


@pytest.fixture
def construir(tmp_path):
    """Devolve (cliente, dormidas): a lista registra o que teria sido dormido."""
    def fabricar():
        dormidas: list[float] = []
        cliente = Cliente(
            token="tok",
            cache=Cache(tmp_path / "cache.sqlite"),
            agora=lambda: AGORA,
            dormir=dormidas.append,
        )
        return cliente, dormidas
    return fabricar


# --- espera de cota -----------------------------------------------------

@responses.activate
def test_remaining_baixo_dorme_ate_o_reset(construir):
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "0",
                           "X-RateLimit-Reset": str(AGORA + 100)})
    responses.get(OUTRA, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "4999",
                           "X-RateLimit-Reset": str(AGORA + 3600)})

    cliente.get(URL)
    assert dormidas == [], "não se dorme antes de saber que a cota acabou"

    cliente.get(OUTRA)
    assert dormidas == [101.0], "deveria dormir até o Reset, com 1 s de margem"


@responses.activate
def test_remaining_confortavel_nao_dorme(construir):
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "4999",
                           "X-RateLimit-Reset": str(AGORA + 3600)})
    responses.get(OUTRA, json=[], status=200)

    cliente.get(URL)
    cliente.get(OUTRA)

    assert dormidas == []


@responses.activate
def test_reset_no_passado_nao_dorme_tempo_negativo(construir):
    # Relógio local adiantado em relação ao do GitHub.
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "0",
                           "X-RateLimit-Reset": str(AGORA - 500)})
    responses.get(OUTRA, json=[], status=200)

    cliente.get(URL)
    cliente.get(OUTRA)

    assert all(s >= 0 for s in dormidas), f"dormiu tempo negativo: {dormidas}"


@responses.activate
def test_cabecalho_de_cota_malformado_nao_quebra(construir):
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "muitas",
                           "X-RateLimit-Reset": "nunca"})
    responses.get(OUTRA, json=[], status=200)

    cliente.get(URL)
    assert cliente.get(OUTRA).status == 200


@responses.activate
def test_acerto_de_cache_nao_espera_cota(construir):
    # Servir do cache não gasta cota, então não pode dormir.
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "0",
                           "X-RateLimit-Reset": str(AGORA + 100)})

    cliente.get(URL)
    cliente.get(URL)

    assert dormidas == []


# --- 403 / 429 ----------------------------------------------------------

@responses.activate
def test_403_com_retry_after_espera_e_repete(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "You have exceeded a secondary rate limit"},
                  status=403, headers={"Retry-After": "30"})
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)

    r = cliente.get(URL)

    assert r.status == 200
    assert dormidas == [30.0]
    assert len(responses.calls) == 2


@responses.activate
def test_429_com_retry_after_espera_e_repete(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "Too many requests"}, status=429,
                  headers={"Retry-After": "5"})
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [5.0]


@responses.activate
def test_403_com_remaining_zero_espera_ate_o_reset(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "Forbidden"}, status=403,
                  headers={"X-RateLimit-Remaining": "0",
                           "X-RateLimit-Reset": str(AGORA + 60)})
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [61.0]


@responses.activate
def test_403_de_permissao_levanta_sem_repetir(construir):
    # Repetir cinco vezes um 403 de permissão só queima cota e esconde o erro.
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "Must have admin rights to Repository."},
                  status=403)

    with pytest.raises(ErroDeHTTP) as erro:
        cliente.get(URL)

    assert erro.value.status == 403
    assert len(responses.calls) == 1
    assert dormidas == []


@responses.activate
def test_retry_after_como_data_http_cai_no_reset(construir):
    # O RFC permite data em vez de segundos; float() estouraria.
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "rate limit"}, status=403,
                  headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT",
                           "X-RateLimit-Reset": str(AGORA + 10)})
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [11.0]


@responses.activate
def test_rate_limit_sem_cabecalho_nenhum_usa_espera_padrao(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "API rate limit exceeded"}, status=403)
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [60.0]


@responses.activate
def test_rate_limit_persistente_desiste(construir):
    cliente, dormidas = construir()
    for _ in range(10):
        responses.get(URL, json={"message": "API rate limit exceeded"}, status=403,
                      headers={"Retry-After": "1"})

    with pytest.raises(ErroDeHTTP, match="rate limit"):
        cliente.get(URL)

    assert len(dormidas) == 5, "o teto de esperas de cota é 5"


# --- 5xx e rede ---------------------------------------------------------

@responses.activate
def test_502_502_200(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "Bad gateway"}, status=502)
    responses.get(URL, json={"message": "Bad gateway"}, status=502)
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)

    r = cliente.get(URL)

    assert r.status == 200
    assert r.json() == [{"tag_name": "v1"}]
    assert dormidas == [1, 2], "backoff 1 s depois 2 s"
    assert len(responses.calls) == 3


@responses.activate
def test_5xx_persistente_esgota_o_backoff(construir):
    cliente, dormidas = construir()
    for _ in range(len(ESPERAS_5XX) + 1):
        responses.get(URL, json={"message": "Internal"}, status=500)

    with pytest.raises(ErroDeHTTP) as erro:
        cliente.get(URL)

    assert erro.value.status == 500
    assert dormidas == list(ESPERAS_5XX), "esperas 1, 2, 4, 8, 16"
    assert len(responses.calls) == len(ESPERAS_5XX) + 1


@responses.activate
def test_erro_de_rede_tambem_tem_backoff(construir):
    cliente, dormidas = construir()
    responses.get(URL, body=requests.ConnectionError("conexao caiu"))
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [1]


@responses.activate
def test_erro_de_rede_persistente_levanta(construir):
    cliente, dormidas = construir()
    for _ in range(len(ESPERAS_5XX) + 1):
        responses.get(URL, body=requests.ConnectionError("conexao caiu"))

    with pytest.raises(ErroDeHTTP, match="rede"):
        cliente.get(URL)


# --- nada disso entra no cache ------------------------------------------

@responses.activate
def test_5xx_nunca_entra_no_cache(construir):
    cliente, _ = construir()
    for _ in range(len(ESPERAS_5XX) + 1):
        responses.get(URL, json={"message": "Internal"}, status=500)

    with pytest.raises(ErroDeHTTP):
        cliente.get(URL)

    assert cliente._cache.ler(chave_de("GET", URL)) is None


@responses.activate
def test_403_nunca_entra_no_cache(construir):
    cliente, _ = construir()
    responses.get(URL, json={"message": "Must have admin rights."}, status=403)

    with pytest.raises(ErroDeHTTP):
        cliente.get(URL)

    assert cliente._cache.ler(chave_de("GET", URL)) is None


# --- cada balde de cota tem a sua própria contagem -----------------------

BUSCA = "https://api.github.com/search/repositories"


@responses.activate
def test_balde_de_busca_nao_faz_o_cliente_dormir_a_toa(construir):
    # O balde de busca autenticada é de 30 por minuto, então Remaining ali
    # está SEMPRE abaixo do limiar de 50 do balde core. Tratar os dois como
    # um só faria o cliente dormir ~1 min depois de cada busca — e a Issue
    # #41 faz centenas delas.
    cliente, dormidas = construir()
    for restantes in ("29", "28", "27"):
        responses.get(BUSCA, json={"items": []}, status=200,
                      headers={"X-RateLimit-Remaining": restantes,
                               "X-RateLimit-Reset": str(AGORA + 58),
                               "X-RateLimit-Limit": "30",
                               "X-RateLimit-Resource": "search"})

    cliente.get(BUSCA, {"q": "a"})
    cliente.get(BUSCA, {"q": "b"})
    cliente.get(BUSCA, {"q": "c"})

    assert dormidas == [], f"dormiu sem precisar entre buscas: {dormidas}"


@responses.activate
def test_cota_de_busca_nao_contamina_a_cota_core(construir):
    cliente, dormidas = construir()
    responses.get(BUSCA, json={"items": []}, status=200,
                  headers={"X-RateLimit-Remaining": "1",
                           "X-RateLimit-Reset": str(AGORA + 58),
                           "X-RateLimit-Limit": "30",
                           "X-RateLimit-Resource": "search"})
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "4987",
                           "X-RateLimit-Reset": str(AGORA + 3500),
                           "X-RateLimit-Limit": "5000",
                           "X-RateLimit-Resource": "core"})

    cliente.get(BUSCA, {"q": "a"})
    cliente.get(URL)

    assert dormidas == [], "a chamada core tinha 4987 de cota e mesmo assim dormiu"


@responses.activate
def test_balde_de_busca_esgotado_ainda_dorme(construir):
    # O limiar encolhe junto com o balde, mas não some.
    cliente, dormidas = construir()
    responses.get(BUSCA, json={"items": []}, status=200,
                  headers={"X-RateLimit-Remaining": "1",
                           "X-RateLimit-Reset": str(AGORA + 58),
                           "X-RateLimit-Limit": "30",
                           "X-RateLimit-Resource": "search"})
    responses.get(BUSCA, json={"items": []}, status=200)

    cliente.get(BUSCA, {"q": "a"})
    cliente.get(BUSCA, {"q": "b"})

    assert dormidas == [59.0]


@responses.activate
def test_remaining_sem_reset_nao_se_junta_ao_reset_de_outra_resposta(construir):
    # Remaining da resposta 1 + Reset da resposta 2 = uma espera inventada.
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "3"})
    responses.get(OUTRA, json=[], status=200,
                  headers={"X-RateLimit-Reset": str(AGORA + 600)})
    responses.get("https://api.github.com/repos/a/b/issues", json=[], status=200)

    cliente.get(URL)
    cliente.get(OUTRA)
    cliente.get("https://api.github.com/repos/a/b/issues")

    assert dormidas == [], f"dormiu com um par de cota remendado: {dormidas}"


@responses.activate
def test_cabecalho_de_cota_infinito_ou_nan_nao_derruba_a_coleta(construir):
    # float("inf") passa pelo float() e estoura no int(); time.sleep(nan)
    # levanta ValueError. Nenhum dos dois pode matar uma coleta de 100 repos.
    cliente, dormidas = construir()
    responses.get(URL, json=[], status=200,
                  headers={"X-RateLimit-Remaining": "inf",
                           "X-RateLimit-Reset": "nan"})
    responses.get(OUTRA, json=[], status=200)

    cliente.get(URL)

    assert cliente.get(OUTRA).status == 200
    assert all(s == s for s in dormidas), f"dormiu NaN: {dormidas}"


@responses.activate
def test_retry_after_nan_cai_na_espera_padrao(construir):
    cliente, dormidas = construir()
    responses.get(URL, json={"message": "rate limit"}, status=403,
                  headers={"Retry-After": "nan"})
    responses.get(URL, json=[], status=200)

    assert cliente.get(URL).status == 200
    assert dormidas == [ESPERA_PADRAO_S]
