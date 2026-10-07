"""O cache é persistência pura: nada de rede, nada de HTTP."""
import json
import sqlite3

import pytest

from coleta.cache import CAMINHO_PADRAO, Cache, RespostaCacheada, chave_de


@pytest.fixture
def cache(tmp_path):
    c = Cache(tmp_path / "cache.sqlite")
    yield c
    c.fechar()


def test_chave_ignora_a_ordem_dos_params():
    a = chave_de("GET", "https://api.github.com/x", {"b": 2, "a": 1})
    b = chave_de("GET", "https://api.github.com/x", {"a": 1, "b": 2})
    assert a == b


def test_chave_trata_numero_e_texto_como_iguais():
    # per_page=100 e per_page="100" geram a mesma requisição; forçar um miss
    # aqui custaria cota à toa.
    assert chave_de("GET", "u", {"per_page": 100}) == chave_de("GET", "u", {"per_page": "100"})


def test_chave_descarta_params_nulos():
    # requests omite da query os parâmetros com valor None. Mantê-los na chave
    # faria duas requisições idênticas caírem em linhas diferentes do cache.
    assert chave_de("GET", "u", {"a": 1, "b": None}) == chave_de("GET", "u", {"a": 1})


def test_chave_sem_params_e_com_dict_vazio_sao_iguais():
    assert chave_de("GET", "u") == chave_de("GET", "u", {})


def test_chave_muda_com_url_metodo_e_params():
    base = chave_de("GET", "https://api.github.com/x", {"a": 1})
    assert base != chave_de("GET", "https://api.github.com/y", {"a": 1})
    assert base != chave_de("POST", "https://api.github.com/x", {"a": 1})
    assert base != chave_de("GET", "https://api.github.com/x", {"a": 2})


def test_chave_nao_depende_do_token(monkeypatch):
    # O cache vale para qualquer GITHUB_TOKEN: uma resposta guardada com o
    # token de um integrante serve para os outros.
    monkeypatch.setenv("GITHUB_TOKEN", "token_de_alguem")
    primeira = chave_de("GET", "https://api.github.com/x", {"a": 1})
    monkeypatch.setenv("GITHUB_TOKEN", "token_de_outro")
    assert chave_de("GET", "https://api.github.com/x", {"a": 1}) == primeira


def test_le_chave_ausente_devolve_none(cache):
    assert cache.ler(chave_de("GET", "https://api.github.com/nada")) is None


def test_grava_e_le_resposta_de_sucesso(cache):
    chave = chave_de("GET", "https://api.github.com/x", {"a": 1})
    cache.gravar(chave, "GET", "https://api.github.com/x", {"a": 1},
                 200, {"Link": "<u>; rel=\"next\""}, '{"ok": true}')

    lida = cache.ler(chave)
    assert lida == RespostaCacheada(
        status=200, cabecalhos={"Link": '<u>; rel="next"'}, corpo='{"ok": true}'
    )


def test_grava_e_le_404(cache):
    # O 404 é cacheado de propósito: evita repetir um compare quebrado.
    chave = chave_de("GET", "https://api.github.com/some/compare")
    cache.gravar(chave, "GET", "https://api.github.com/some/compare", None,
                 404, {}, '{"message": "Not Found"}')
    assert cache.ler(chave).status == 404


def test_regravar_a_mesma_chave_substitui(cache):
    chave = chave_de("GET", "https://api.github.com/x")
    cache.gravar(chave, "GET", "https://api.github.com/x", None, 200, {}, "antigo")
    cache.gravar(chave, "GET", "https://api.github.com/x", None, 200, {}, "novo")

    assert cache.ler(chave).corpo == "novo"
    with sqlite3.connect(str(cache.caminho)) as con:
        assert con.execute("SELECT COUNT(*) FROM respostas").fetchone()[0] == 1


def test_persiste_entre_instancias(tmp_path):
    # É isto que faz a retomada funcionar: matar o processo e rodar de novo
    # não pode refazer chamadas já salvas.
    caminho = tmp_path / "cache.sqlite"
    chave = chave_de("GET", "https://api.github.com/x")

    primeira = Cache(caminho)
    primeira.gravar(chave, "GET", "https://api.github.com/x", None, 200, {}, "corpo")
    primeira.fechar()

    segunda = Cache(caminho)
    assert segunda.ler(chave).corpo == "corpo"
    segunda.fechar()


def test_cria_a_pasta_do_banco(tmp_path):
    caminho = tmp_path / "data" / "raw" / "cache.sqlite"
    c = Cache(caminho)
    c.fechar()
    assert caminho.exists()


def test_guarda_url_e_params_em_claro_para_depurar(cache):
    chave = chave_de("GET", "https://api.github.com/x", {"b": 2, "a": 1})
    cache.gravar(chave, "get", "https://api.github.com/x", {"b": 2, "a": 1}, 200, {}, "{}")

    with sqlite3.connect(str(cache.caminho)) as con:
        metodo, url, params = con.execute(
            "SELECT metodo, url, params FROM respostas WHERE chave = ?", (chave,)
        ).fetchone()
    assert metodo == "GET"
    assert url == "https://api.github.com/x"
    assert json.loads(params) == {"a": "1", "b": "2"}


def test_caminho_padrao_fica_em_data_raw():
    assert CAMINHO_PADRAO == "data/raw/cache.sqlite"
