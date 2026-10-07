"""Orquestrador do pipeline (#39): etapas injetadas, sem rede."""
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
import responses

from coleta import http
from coleta.cache import Cache
from coleta.runs import Coleta
from metricas.schemas import SCHEMAS, df_vazio
from pipeline import __main__ as cli
from pipeline.config import Config
from pipeline.executar import ARQUIVOS, executar


def _cfg(**kw):
    base = dict(
        janela_inicio=date(2024, 1, 1), janela_fim=date(2024, 12, 31),
        faixas_estrelas=["1000..2000"], min_releases=5, min_runs=50,
        n_repos=100, seed=42, ambientes_producao=["production"],
        labels_bug=["bug"], n_dias_issue=7, bots=["dependabot[bot]"],
        _janela_placeholder=False,
    )
    base.update(kw)
    return Config(**base)


@pytest.fixture(autouse=True)
def cliente(tmp_path):
    c = http.Cliente(token="t", cache=Cache(tmp_path / "cache.sqlite"),
                     dormir=lambda s: None)
    http.redefinir_cliente(c)
    yield c
    http.redefinir_cliente(None)


def _run(repo, i, classe, quando):
    return {
        "repo": repo, "run_id": i, "workflow_id": 1, "workflow_nome": "ci",
        "event": "push", "head_sha": f"s{i}", "run_attempt": 1,
        "conclusion": "success" if classe == "sucesso" else "failure",
        "classe": classe, "inicio": quando, "fim": quando, "criado_em": quando,
    }


def _etapas(repos, **sobrescreve):
    vistos = {}

    def selecionar(cfg, pasta):
        vistos["n_repos"] = cfg.n_repos
        return pd.DataFrame({"repo": repos[: cfg.n_repos]})

    def releases(repo, cfg, session):
        rel = pd.DataFrame([{
            "repo": repo, "tag": "v1.0.0", "publicada_em": "2024-03-01T00:00:00Z",
            "prerelease": False, "na_janela": True, "body": "",
        }])
        return rel, df_vazio(SCHEMAS["tags"])

    def commits(repo, rel, cfg, session):
        return df_vazio(SCHEMAS["commits"]), df_vazio(SCHEMAS["releases_ignoradas"])

    def deployments(repo, cfg, session):
        return df_vazio(SCHEMAS["deployments"])

    def coletar_repos(lista, cfg, commits_df):
        return pd.DataFrame([{
            "repo": r, "estrelas": 1500, "linguagem": "Python",
            "criado_em": "2020-01-01T00:00:00Z", "idade_anos": 4.0,
            "default_branch": "main", "contribuidores": 3, "owner_tipo": "User",
            "org_verificada": False, "automacao_release": False,
            "ferramenta_release": "nenhuma", "pct_conventional": 0.5,
        } for r in lista], columns=list(SCHEMAS["repos"].colunas))

    def runs(repo, branch, inicio, fim):
        linhas = [_run(repo, i, "sucesso", f"2024-03-{i + 1:02d}T10:00:00Z") for i in range(6)]
        return Coleta(runs=linhas, saturadas=[])

    def tentativas(repo, linhas, max_t):
        return []

    def issues(repo, labels, inicio, tags):
        return []

    etapas = SimpleNamespace(
        selecionar=selecionar, coletar_releases=releases, coletar_commits=commits,
        coletar_deployments=deployments, coletar_repos=coletar_repos,
        coletar_runs=runs, coletar_tentativas=tentativas, coletar_issues_bug=issues,
        session=object(), vistos=vistos,
    )
    for k, v in sobrescreve.items():
        setattr(etapas, k, v)
    return etapas


def test_limite_vira_n_repos(tmp_path):
    e = _etapas(["o/a", "o/b", "o/c", "o/d", "o/e"])
    executar(_cfg(), limite=3, pasta=tmp_path, etapas=e)
    assert e.vistos["n_repos"] == 3


def test_sem_limite_usa_n_repos_do_config(tmp_path):
    e = _etapas(["o/a", "o/b"])
    executar(_cfg(n_repos=2), pasta=tmp_path, etapas=e)
    assert e.vistos["n_repos"] == 2


def test_grava_todos_os_csvs_do_contrato(tmp_path):
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a", "o/b"]))
    for nome, chave in ARQUIVOS.items():
        arquivo = tmp_path / nome
        assert arquivo.exists(), nome
        # o cabeçalho é o contrato; a validação de tipos roda antes de gravar
        assert list(pd.read_csv(arquivo).columns) == list(SCHEMAS[chave].colunas), nome
    metricas = pd.read_csv(tmp_path / "metricas.csv")
    assert sorted(metricas["repo"]) == ["o/a", "o/b"]
    assert metricas["cfr_a"].notna().all()


def test_repo_que_falha_nao_derruba_os_outros(tmp_path):
    def releases(repo, cfg, session):
        if repo == "o/ruim":
            raise RuntimeError("502 depois de todas as tentativas")
        return _etapas([]).coletar_releases(repo, cfg, session)

    e = _etapas(["o/ruim", "o/bom"], coletar_releases=releases)
    r = executar(_cfg(), pasta=tmp_path, etapas=e)
    assert list(r["falhas"]) == ["o/ruim"]
    assert "502" in r["falhas"]["o/ruim"]
    assert pd.read_csv(tmp_path / "metricas.csv")["repo"].tolist() == ["o/bom"]
    assert (tmp_path / "custo_api.csv").exists()


def test_custo_gravado_mesmo_em_ctrl_c(tmp_path):
    def releases(repo, cfg, session):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a"], coletar_releases=releases))
    assert (tmp_path / "custo_api.csv").exists()


def test_zero_aprovados_gera_csvs_vazios_validos(tmp_path):
    executar(_cfg(), pasta=tmp_path, etapas=_etapas([]))
    for nome, chave in ARQUIVOS.items():
        assert (tmp_path / nome).exists(), nome
    assert pd.read_csv(tmp_path / "metricas.csv").empty


def test_repo_sem_runs_fica_nan_no_cfr(tmp_path):
    e = _etapas(["o/a"], coletar_runs=lambda *a: Coleta(runs=[], saturadas=[]))
    executar(_cfg(), pasta=tmp_path, etapas=e)
    assert pd.read_csv(tmp_path / "metricas.csv")["cfr_a"].isna().all()


def test_repo_sem_metadados_sai_do_resultado_e_e_registrado(tmp_path):
    def sem_o_ruim(lista, cfg, commits_df):
        return _etapas([]).coletar_repos([r for r in lista if r != "o/b"], cfg, commits_df)

    e = _etapas(["o/a", "o/b"], coletar_repos=sem_o_ruim)
    r = executar(_cfg(), pasta=tmp_path, etapas=e)
    assert "o/b" in r["falhas"]
    assert pd.read_csv(tmp_path / "metricas.csv")["repo"].tolist() == ["o/a"]


@responses.activate
def test_segunda_rodada_nao_chama_a_api(tmp_path, cliente):
    url = "https://api.github.com/repos/o/a/releases"
    responses.add(responses.GET, url, json=[])

    def releases(repo, cfg, session):
        session.get(url)
        return _etapas([]).coletar_releases(repo, cfg, session)

    from coleta.sessao import SessaoHttp
    e = _etapas(["o/a"], coletar_releases=releases, session=SessaoHttp())
    executar(_cfg(), pasta=tmp_path / "1", etapas=e)
    cliente._custo.clear()
    executar(_cfg(), pasta=tmp_path / "2", etapas=e)
    custo = pd.read_csv(tmp_path / "2" / "custo_api.csv")
    assert custo["chamadas"].sum() == 0
    assert custo["do_cache"].sum() >= 1
    assert len(responses.calls) == 1


# --- linha de comando -------------------------------------------------------

@pytest.mark.parametrize("valor", ["0", "-2"])
def test_cli_limite_invalido_e_erro_de_uso(valor, capsys):
    assert cli.main(["--limite", valor]) == 2
    assert "limite" in capsys.readouterr().err


def test_cli_janela_placeholder_recusa(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "janela: {inicio: 2024-10-01, fim: 2025-09-30, placeholder: true}\n"
        "faixas_estrelas: ['1000..2000']\nmin_releases: 5\nmin_runs: 50\n"
        "n_repos: 100\nseed: 42\nambientes_producao: [production]\n"
        "labels_bug: [bug]\nn_dias_issue: 7\nbots: ['dependabot[bot]']\n",
        encoding="utf-8",
    )
    assert cli.main(["--config", str(cfg)]) == 2
    assert "placeholder" in capsys.readouterr().err
