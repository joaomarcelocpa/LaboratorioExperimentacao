"""Orquestrador do pipeline (#39): etapas injetadas, sem rede."""
from datetime import date
from pathlib import Path
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
from pipeline.executar import ARQUIVOS, COMPACTADOS, caminho_saida, executar


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
        arquivo = caminho_saida(tmp_path, nome)
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
        assert caminho_saida(tmp_path, nome).exists(), nome
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


def test_funil_fecha_com_limite(tmp_path):
    from coleta.filtros import df_funil, funil_fecha, sortear

    def selecionar(cfg, pasta):
        aprovados = ["o/a", "o/b", "o/c", "o/d", "o/e"]
        amostra, _, etapa = sortear(aprovados, cfg.n_repos, cfg.seed)
        funil = df_funil([
            {"etapa": "usa_actions", "entraram": 6, "sairam": 1, "motivo": "sem Actions"},
            etapa,
        ])
        funil.to_csv(Path(pasta) / "funil.csv", index=False)
        return pd.DataFrame({"repo": amostra})

    e = _etapas([], selecionar=selecionar)
    r = executar(_cfg(), limite=3, pasta=tmp_path, etapas=e)
    funil = pd.read_csv(tmp_path / "funil.csv")
    assert len(r["repos"]) == 3
    assert funil_fecha(funil, 3)
    assert funil["etapa"].iloc[-1] == "sorteio"


# --- achados da revisão final -------------------------------------------------

def test_401_aborta_a_rodada_em_vez_de_virar_falha_por_repo(tmp_path):
    def releases(repo, cfg, session):
        raise http.ErroDeHTTP("Bad credentials", 401)

    with pytest.raises(http.ErroDeHTTP):
        executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a", "o/b"], coletar_releases=releases))
    assert (tmp_path / "custo_api.csv").exists()


def test_401_em_runs_tambem_aborta(tmp_path):
    def runs(*a):
        raise http.ErroDeHTTP("Bad credentials", 401)

    with pytest.raises(http.ErroDeHTTP):
        executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"], coletar_runs=runs))


def test_cli_sai_com_1_quando_nenhum_repo_sobreviveu(monkeypatch, tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "janela: {inicio: 2024-10-01, fim: 2025-09-30}\n"
        "faixas_estrelas: ['1000..2000']\nmin_releases: 5\nmin_runs: 50\n"
        "n_repos: 100\nseed: 42\nambientes_producao: [production]\n"
        "labels_bug: [bug]\nn_dias_issue: 7\nbots: ['dependabot[bot]']\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("pipeline.executar.executar",
                        lambda *a, **k: {"repos": [], "falhas": {"o/a": "boom"}})
    assert cli.main(["--config", str(cfg)]) == 1


def test_erro_inesperado_em_coletar_repos_so_derruba_o_repo_ruim(tmp_path):
    def repos(lista, cfg, commits_df):
        if "o/b" in lista and len(lista) > 1:
            raise ValueError("rel=last sem número de página")
        if lista == ["o/b"]:
            raise ValueError("rel=last sem número de página")
        return _etapas([]).coletar_repos(lista, cfg, commits_df)

    r = executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a", "o/b"], coletar_repos=repos))
    assert r["repos"] == ["o/a"]
    assert "o/b" in r["falhas"]
    assert pd.read_csv(tmp_path / "metricas.csv")["repo"].tolist() == ["o/a"]


def test_repo_que_falha_em_runs_sai_de_todas_as_saidas(tmp_path):
    def runs(repo, branch, inicio, fim):
        if repo == "o/ruim":
            raise KeyError("total_count")
        return _etapas([]).coletar_runs(repo, branch, inicio, fim)

    r = executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/ruim", "o/bom"], coletar_runs=runs))
    assert "o/ruim" in r["falhas"]
    for nome in ("repos.csv", "metricas.csv"):
        assert pd.read_csv(tmp_path / nome)["repo"].tolist() == ["o/bom"], nome


def test_fatias_saturadas_de_rodada_anterior_nao_sobrevive(tmp_path):
    velho = tmp_path / "fatias_saturadas.csv"
    velho.write_text("repo,inicio,fim,total_count\no/x,a,b,1000\n")
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"]))
    assert not velho.exists()


def test_custo_da_selecao_e_gravado_a_parte(tmp_path):
    def selecionar(cfg, pasta):
        http.get  # a seleção "gasta" uma chamada contada pelo cliente
        http.cliente_padrao()._contar("https://api.github.com/search/repositories", "chamadas")
        return pd.DataFrame({"repo": ["o/a"]})

    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"], selecionar=selecionar))
    sel = pd.read_csv(tmp_path / "custo_selecao.csv")
    assert sel["chamadas"].sum() == 1


# --- checkpoints: algo para entregar mesmo se a rodada for interrompida --------

def _repos_em(pasta, nome):
    return sorted(pd.read_csv(caminho_saida(pasta, nome))["repo"].unique())


def test_ctrl_c_no_segundo_repo_deixa_o_primeiro_completo_em_todos_os_csvs(tmp_path):
    def runs(repo, branch, inicio, fim):
        if repo == "o/b":
            raise KeyboardInterrupt
        return _etapas([]).coletar_runs(repo, branch, inicio, fim)

    with pytest.raises(KeyboardInterrupt):
        executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a", "o/b"], coletar_runs=runs))
    for nome in ("repos.csv", "metricas.csv", "releases.csv", "runs.csv"):
        # o/b já tinha releases coletadas quando caiu, mas não ficou completo
        assert _repos_em(tmp_path, nome) == ["o/a"], nome
    assert (tmp_path / "custo_api.csv").exists()


def test_o_checkpoint_e_gravado_depois_de_cada_repo(tmp_path):
    vistos = []

    def releases(repo, cfg, session):
        if repo == "o/b":  # no começo do 2º repo, o 1º já tem de estar no disco
            vistos.extend(_repos_em(tmp_path, "metricas.csv"))
        return _etapas([]).coletar_releases(repo, cfg, session)

    executar(_cfg(), pasta=tmp_path,
             etapas=_etapas(["o/a", "o/b"], coletar_releases=releases))
    assert vistos == ["o/a"]


def test_401_no_meio_preserva_o_que_ja_estava_completo(tmp_path):
    def releases(repo, cfg, session):
        if repo == "o/b":
            raise http.ErroDeHTTP("Bad credentials", 401)
        return _etapas([]).coletar_releases(repo, cfg, session)

    with pytest.raises(http.ErroDeHTTP):
        executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a", "o/b"], coletar_releases=releases))
    assert _repos_em(tmp_path, "metricas.csv") == ["o/a"]


def test_metadados_sao_pedidos_repo_a_repo(tmp_path):
    pedidos = []

    def repos(lista, cfg, commits_df):
        pedidos.append(list(lista))
        return _etapas([]).coletar_repos(lista, cfg, commits_df)

    executar(_cfg(), pasta=tmp_path,
             etapas=_etapas(["o/a", "o/b"], coletar_repos=repos))
    assert pedidos == [["o/a"], ["o/b"]]


def test_gravacao_nao_deixa_arquivo_temporario(tmp_path):
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a", "o/b"]))
    assert not [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


# --- erro no finally não pode mascarar o erro original (Issue #65) --------------

def test_erro_original_aparece_quando_a_gravacao_do_custo_tambem_falha(tmp_path, monkeypatch, capsys):
    def selecionar(cfg, pasta):
        raise ValueError("a busca quebrou")

    def custo_quebrado(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(http, "escrever_custo_api", custo_quebrado)
    with pytest.raises(ValueError, match="a busca quebrou"):
        executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"], selecionar=selecionar))
    assert "disco cheio" in capsys.readouterr().err   # o 2º erro é avisado, não engolido


def test_ctrl_c_continua_sendo_ctrl_c_se_o_custo_falhar(tmp_path, monkeypatch):
    def releases(repo, cfg, session):
        raise KeyboardInterrupt

    monkeypatch.setattr(http, "escrever_custo_api",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disco cheio")))
    with pytest.raises(KeyboardInterrupt):
        executar(_cfg(), pasta=tmp_path,
                 etapas=_etapas(["o/a"], coletar_releases=releases))


def test_sem_erro_original_a_falha_do_custo_aparece(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "escrever_custo_api",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disco cheio")))
    with pytest.raises(OSError, match="disco cheio"):
        executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"]))


# --- fatias: saturação real separada de erro de API (Issue #65) ---------------------

def _fatia(repo, motivo, total=1000):
    from coleta.runs import FatiaSaturada
    return FatiaSaturada(repo, "2025-10-01T00:00:00Z", "2025-10-31T23:59:59Z", total, motivo)


def test_fatias_saturadas_so_tem_saturacao_real(tmp_path):
    def runs(repo, branch, inicio, fim):
        return Coleta(runs=[], saturadas=[
            _fatia(repo, "teto", 1500), _fatia(repo, "erro 403", 0),
            _fatia(repo, "erro 422", 0)])

    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"], coletar_runs=runs))
    sat = pd.read_csv(tmp_path / "fatias_saturadas.csv")
    nao = pd.read_csv(tmp_path / "fatias_nao_coletadas.csv")
    assert sat["total_count"].tolist() == [1500] and list(sat.columns) == [
        "repo", "inicio", "fim", "total_count"]
    assert sorted(nao["motivo"]) == ["erro 403", "erro 422"]


def test_sem_nada_a_registrar_nenhum_dos_dois_arquivos_existe(tmp_path):
    (tmp_path / "fatias_nao_coletadas.csv").write_text("repo,inicio,fim,motivo\no/x,a,b,erro 403\n")
    (tmp_path / "fatias_saturadas.csv").write_text("repo,inicio,fim,total_count\no/x,a,b,1000\n")
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"]))
    assert not (tmp_path / "fatias_saturadas.csv").exists()
    assert not (tmp_path / "fatias_nao_coletadas.csv").exists()


def test_so_erro_de_api_nao_cria_fatias_saturadas(tmp_path):
    def runs(repo, branch, inicio, fim):
        return Coleta(runs=[], saturadas=[_fatia(repo, "erro 403", 0)])

    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"], coletar_runs=runs))
    assert not (tmp_path / "fatias_saturadas.csv").exists()
    assert (tmp_path / "fatias_nao_coletadas.csv").exists()


# --- commits.csv e runs.csv passam de 100 MB: saem em .gz (Issue #65) ---------------

def test_commits_e_runs_saem_comprimidos_e_sem_o_arquivo_grande(tmp_path):
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a", "o/b"]))
    assert COMPACTADOS == ("commits.csv", "runs.csv")
    for nome in COMPACTADOS:
        assert (tmp_path / f"{nome}.gz").exists(), nome
        assert not (tmp_path / nome).exists(), f"{nome} puro não pode sobrar (>100 MB)"
        cols = list(pd.read_csv(tmp_path / f"{nome}.gz").columns)
        assert cols == list(SCHEMAS[ARQUIVOS[nome]].colunas)
    assert sorted(pd.read_csv(tmp_path / "runs.csv.gz")["repo"].unique()) == ["o/a", "o/b"]


def test_os_outros_csvs_continuam_planos(tmp_path):
    executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a"]))
    for nome in ARQUIVOS:
        if nome not in COMPACTADOS:
            assert (tmp_path / nome).exists() and not (tmp_path / f"{nome}.gz").exists()


def test_checkpoint_e_plano_e_so_o_final_comprime(tmp_path):
    visto = {}

    def releases(repo, cfg, session):
        if repo == "o/b":   # o 1º repo já passou pelo checkpoint
            visto["plano"] = (tmp_path / "runs.csv").exists()
            visto["gz"] = (tmp_path / "runs.csv.gz").exists()
        return _etapas([]).coletar_releases(repo, cfg, session)

    executar(_cfg(), pasta=tmp_path,
             etapas=_etapas(["o/a", "o/b"], coletar_releases=releases))
    assert visto == {"plano": True, "gz": False}      # comprimir a cada repo custaria horas
    assert (tmp_path / "runs.csv.gz").exists() and not (tmp_path / "runs.csv").exists()


def test_interrompido_tambem_deixa_o_gz_com_o_que_estava_completo(tmp_path):
    def runs(repo, branch, inicio, fim):
        if repo == "o/b":
            raise KeyboardInterrupt
        return _etapas([]).coletar_runs(repo, branch, inicio, fim)

    with pytest.raises(KeyboardInterrupt):
        executar(_cfg(), pasta=tmp_path, etapas=_etapas(["o/a", "o/b"], coletar_runs=runs))
    assert sorted(pd.read_csv(tmp_path / "runs.csv.gz")["repo"].unique()) == ["o/a"]
    assert not (tmp_path / "runs.csv").exists()
    assert (tmp_path / "custo_api.csv").exists()


def test_o_gz_e_reprodutivel_byte_a_byte(tmp_path):
    import hashlib, time

    def rodar(pasta):
        executar(_cfg(), pasta=pasta, etapas=_etapas(["o/a", "o/b"]))
        return hashlib.md5((pasta / "commits.csv.gz").read_bytes()).hexdigest()

    a = rodar(tmp_path / "1")
    time.sleep(1.1)       # um relógio no cabeçalho do gzip mudaria o resultado
    assert rodar(tmp_path / "2") == a


def test_caminho_saida_prefere_o_plano_em_andamento_e_cai_no_gz(tmp_path):
    (tmp_path / "runs.csv.gz").write_bytes(b"x")
    assert caminho_saida(tmp_path, "runs.csv") == tmp_path / "runs.csv.gz"
    (tmp_path / "runs.csv").write_text("x")
    assert caminho_saida(tmp_path, "runs.csv") == tmp_path / "runs.csv"
    assert caminho_saida(tmp_path, "repos.csv") == tmp_path / "repos.csv"
