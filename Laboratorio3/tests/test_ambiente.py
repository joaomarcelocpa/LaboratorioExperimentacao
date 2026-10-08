"""Leitura do .env: o token tem que chegar ao processo sem ser impresso."""
import os

import pytest

from pipeline.ambiente import carregar_env


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OUTRA", raising=False)


def _env(tmp_path, texto):
    caminho = tmp_path / ".env"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def test_carrega_a_variavel(tmp_path):
    carregar_env(_env(tmp_path, "GITHUB_TOKEN=abc123\n"))
    assert os.environ["GITHUB_TOKEN"] == "abc123"


def test_nao_sobrescreve_o_que_ja_esta_no_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "do-shell")
    carregar_env(_env(tmp_path, "GITHUB_TOKEN=do-arquivo\n"))
    assert os.environ["GITHUB_TOKEN"] == "do-shell"


def test_comentarios_linhas_vazias_aspas_e_export(tmp_path):
    carregar_env(_env(tmp_path, '# comentário\n\nexport GITHUB_TOKEN="com aspas"\nOUTRA=\'simples\'\n'))
    assert os.environ["GITHUB_TOKEN"] == "com aspas"
    assert os.environ["OUTRA"] == "simples"


def test_valor_com_igual_e_espacos_nas_pontas(tmp_path):
    carregar_env(_env(tmp_path, "GITHUB_TOKEN =  a=b=c  \n"))
    assert os.environ["GITHUB_TOKEN"] == "a=b=c"


def test_valor_vazio_nao_define_a_variavel(tmp_path):
    carregar_env(_env(tmp_path, "GITHUB_TOKEN=\n"))
    assert "GITHUB_TOKEN" not in os.environ


def test_arquivo_ausente_nao_faz_nada(tmp_path):
    assert carregar_env(tmp_path / "nao-existe") is False


def test_linha_sem_igual_e_ignorada(tmp_path):
    carregar_env(_env(tmp_path, "lixo sem igual\nGITHUB_TOKEN=ok\n"))
    assert os.environ["GITHUB_TOKEN"] == "ok"


def test_main_carrega_o_env_do_diretorio_atual(tmp_path, monkeypatch, capsys):
    from pipeline import __main__ as cli

    (tmp_path / ".env").write_text("GITHUB_TOKEN=segredo-de-teste\n", encoding="utf-8")
    (tmp_path / "c.yaml").write_text(
        "janela: {inicio: 2025-10-01, fim: 2026-09-30}\n"
        "faixas_estrelas: ['1000..2000']\nmin_releases: 5\nmin_runs: 50\n"
        "n_repos: 100\nseed: 42\nambientes_producao: [production]\n"
        "labels_bug: [bug]\nn_dias_issue: 7\nbots: ['dependabot[bot]']\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    visto = {}

    def falso(cfg, limite=None, **kw):
        visto["token"] = os.environ.get("GITHUB_TOKEN")
        return {"repos": ["o/a"], "falhas": {}}

    monkeypatch.setattr("pipeline.executar.executar", falso)
    assert cli.main(["--config", "c.yaml"]) == 0
    assert visto["token"] == "segredo-de-teste"
    saida = capsys.readouterr()
    assert "segredo-de-teste" not in saida.out + saida.err
