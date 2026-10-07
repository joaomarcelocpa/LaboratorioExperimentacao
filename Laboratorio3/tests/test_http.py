"""get(): cache, 404 como resposta, e erros que não devem ser repetidos."""
import pytest
import responses

from coleta.cache import Cache, chave_de
from coleta.http import Cliente, ErroDeHTTP, Resposta, get, redefinir_cliente

URL = "https://api.github.com/repos/torvalds/linux/releases"


@pytest.fixture
def cliente(tmp_path):
    """Cliente sem rede real, sem disco de produção e que nunca dorme."""
    return Cliente(
        token="tok",
        cache=Cache(tmp_path / "cache.sqlite"),
        agora=lambda: 1000.0,
        dormir=lambda s: None,
    )


@responses.activate
def test_primeira_chamada_vai_a_rede_e_devolve_o_corpo(cliente):
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)

    r = cliente.get(URL)

    assert r.status == 200
    assert r.do_cache is False
    assert r.json() == [{"tag_name": "v1"}]
    assert len(responses.calls) == 1


@responses.activate
def test_segunda_chamada_igual_nao_sai_da_maquina(cliente):
    # O critério de aceite da Issue: interromper e rodar de novo não repete
    # chamadas.
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)

    primeira = cliente.get(URL)
    segunda = cliente.get(URL)

    assert len(responses.calls) == 1, "a segunda chamada foi à rede"
    assert segunda.do_cache is True
    assert primeira.do_cache is False
    assert segunda.json() == primeira.json()


@responses.activate
def test_params_diferentes_sao_chamadas_diferentes(cliente):
    responses.get(URL, json=[], status=200)

    cliente.get(URL, {"page": 1})
    cliente.get(URL, {"page": 2})

    assert len(responses.calls) == 2


@responses.activate
def test_cache_sobrevive_a_troca_de_cliente(tmp_path):
    # Dois processos, o mesmo banco: a retomada de verdade.
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)
    comum = dict(token="tok", agora=lambda: 1000.0, dormir=lambda s: None)

    Cliente(cache=Cache(tmp_path / "c.sqlite"), **comum).get(URL)
    segunda = Cliente(cache=Cache(tmp_path / "c.sqlite"), **comum).get(URL)

    assert len(responses.calls) == 1
    assert segunda.do_cache is True


@responses.activate
def test_404_e_resposta_e_fica_cacheado(cliente):
    # Cachear o 404 evita repetir um compare quebrado em toda rodada.
    responses.get(URL, json={"message": "Not Found"}, status=404)

    r = cliente.get(URL)
    de_novo = cliente.get(URL)

    assert r.status == 404
    assert de_novo.status == 404
    assert de_novo.do_cache is True
    assert len(responses.calls) == 1


@responses.activate
def test_401_levanta_sem_repetir(cliente):
    responses.get(URL, json={"message": "Bad credentials"}, status=401)

    with pytest.raises(ErroDeHTTP) as erro:
        cliente.get(URL)

    assert erro.value.status == 401
    assert len(responses.calls) == 1


@responses.activate
def test_erro_nao_recuperavel_nao_entra_no_cache(cliente):
    responses.get(URL, json={"message": "Unprocessable"}, status=422)

    with pytest.raises(ErroDeHTTP):
        cliente.get(URL)

    assert cliente._cache.ler(chave_de("GET", URL)) is None


@responses.activate
def test_manda_o_token_e_a_versao_da_api(cliente):
    responses.get(URL, json=[], status=200)

    cliente.get(URL)

    enviados = responses.calls[0].request.headers
    assert enviados["Authorization"] == "Bearer tok"
    assert enviados["Accept"] == "application/vnd.github+json"
    assert enviados["X-GitHub-Api-Version"] == "2022-11-28"


@responses.activate
def test_sem_token_a_mensagem_diz_o_que_fazer(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    sem_token = Cliente(cache=Cache(tmp_path / "c.sqlite"),
                        agora=lambda: 1000.0, dormir=lambda s: None)

    with pytest.raises(ErroDeHTTP, match="GITHUB_TOKEN"):
        sem_token.get(URL)


@responses.activate
def test_resposta_ja_cacheada_dispensa_o_token(tmp_path, monkeypatch):
    # Um pipeline inteiramente servido pelo cache precisa rodar sem token.
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)
    caminho = tmp_path / "c.sqlite"
    Cliente(token="tok", cache=Cache(caminho),
            agora=lambda: 1000.0, dormir=lambda s: None).get(URL)

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    sem_token = Cliente(cache=Cache(caminho), agora=lambda: 1000.0, dormir=lambda s: None)

    assert sem_token.get(URL).do_cache is True


def test_json_de_corpo_invalido_vira_erro_de_http():
    # O GitHub às vezes devolve HTML de erro. Um JSONDecodeError cru não diz
    # qual chamada quebrou.
    r = Resposta(status=502, cabecalhos={}, corpo="<html>Bad Gateway</html>", do_cache=False)

    with pytest.raises(ErroDeHTTP) as erro:
        r.json()

    assert erro.value.status == 502
    assert "Bad Gateway" in str(erro.value)


@responses.activate
def test_funcao_de_modulo_usa_o_cliente_padrao(cliente):
    responses.get(URL, json=[{"tag_name": "v1"}], status=200)
    redefinir_cliente(cliente)
    try:
        assert get(URL).json() == [{"tag_name": "v1"}]
    finally:
        redefinir_cliente(None)
