"""Seleção, filtros e funil (Issue #43). Sem rede: responses + fixtures à mão."""
import json
import re
from datetime import date

import pandas as pd
import pytest
import responses

from coleta import filtros, selecao
from coleta.cache import Cache
from coleta.http import Cliente, redefinir_cliente
from metricas.schemas import SCHEMAS, validar
from pipeline.config import Config

API = "https://api.github.com"
BUSCA = f"{API}/search/repositories"


@pytest.fixture(autouse=True)
def cliente_sem_rede(tmp_path):
    redefinir_cliente(Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                              agora=lambda: 1000.0, dormir=lambda s: None))
    yield
    redefinir_cliente(None)


def _cfg(**extra):
    base = dict(
        janela_inicio=date(2024, 10, 1), janela_fim=date(2025, 9, 30),
        faixas_estrelas=["1000..2000"], min_releases=5, min_runs=50,
        n_repos=3, seed=42, ambientes_producao=["production"],
        labels_bug=["bug"], n_dias_issue=7, bots=[], _janela_placeholder=False,
    )
    base.update(extra)
    return Config(**base)


def _item(nome, estrelas=1500, fork=False, archived=False, pushed_at=None):
    item = {"full_name": nome, "stargazers_count": estrelas,
            "fork": fork, "archived": archived}
    if pushed_at is not None:
        item["pushed_at"] = pushed_at
    return item


def _busca(itens, total=None, link=None):
    cab = {"Link": link} if link else {}
    responses.add(
        responses.GET, BUSCA, status=200, headers=cab,
        json={"total_count": len(itens) if total is None else total,
              "items": itens},
    )


def _faixa_da_chamada(chamada):
    return re.search(r"stars%3A(\d+)\.\.(\d+)", chamada.request.url).groups()


# --- faixas ---------------------------------------------------------------

def test_intervalo_fechado():
    assert selecao.intervalo_de("1000..2000") == (1000, 2000)


def test_faixa_aberta_exclui_o_proprio_limite_e_ganha_teto():
    assert selecao.intervalo_de(">50000") == (50001, selecao.TETO_DE_ESTRELAS)


@pytest.mark.parametrize("ruim", ["abc", "10..", "5000..1000", ""])
def test_faixa_invalida(ruim):
    with pytest.raises(ValueError):
        selecao.intervalo_de(ruim)


# --- busca com fatiamento --------------------------------------------------

@responses.activate
def test_faixa_que_cabe_nao_e_partida():
    _busca([_item("a/a"), _item("b/b")])
    itens = selecao.buscar_faixa(1000, 2000)
    assert [i["full_name"] for i in itens] == ["a/a", "b/b"]
    assert len(responses.calls) == 1


@responses.activate
def test_faixa_no_teto_de_1000_e_partida_ao_meio():
    # 999 cabe; 1000 já bate o teto da API e precisa ser partido.
    responses.add(responses.GET, BUSCA, status=200,
                  json={"total_count": 1000, "items": [_item("x/x")]})
    _busca([_item("a/a")], total=999)
    _busca([_item("b/b")], total=999)

    itens = selecao.buscar_faixa(1000, 2000)

    faixas = [_faixa_da_chamada(c) for c in responses.calls]
    assert faixas == [("1000", "2000"), ("1000", "1500"), ("1501", "2000")]
    # Os itens da faixa saturada não entram: só os das metades.
    assert [i["full_name"] for i in itens] == ["a/a", "b/b"]


@responses.activate
def test_faixa_de_uma_estrela_so_saturada_colhe_o_que_da(caplog):
    responses.add(responses.GET, BUSCA, status=200,
                  json={"total_count": 1500, "items": [_item("a/a", 7)]})
    itens = selecao.buscar_faixa(7, 7)
    assert [i["full_name"] for i in itens] == ["a/a"]
    assert "saturou" in caplog.text


@responses.activate
def test_segue_a_paginacao():
    _busca([_item("a/a")], total=2,
           link=f'<{BUSCA}?page=2>; rel="next"')
    responses.add(responses.GET, f"{BUSCA}?page=2", status=200,
                  json={"total_count": 2, "items": [_item("b/b")]})
    itens = selecao.buscar_faixa(1000, 2000)
    assert [i["full_name"] for i in itens] == ["a/a", "b/b"]


@responses.activate
def test_faixa_vazia():
    _busca([])
    assert selecao.buscar_faixa(1000, 2000) == []


@responses.activate
def test_resposta_sem_total_count():
    responses.add(responses.GET, BUSCA, status=200, json={"items": []})
    with pytest.raises(KeyError, match="total_count"):
        selecao.buscar_faixa(1000, 2000)


# --- limpeza ---------------------------------------------------------------

def test_duplicata_fork_e_arquivado_saem_uma_vez_cada():
    brutos = [
        {**_item("a/a"), "_faixa": "1000..2000"},
        {**_item("a/a"), "_faixa": "2000..5000"},          # duplicata
        {**_item("b/b", fork=True), "_faixa": "1000..2000"},
        {**_item("c/c", archived=True), "_faixa": "1000..2000"},
        {**_item("d/d", fork=True), "_faixa": "1000..2000"},
        {**_item("d/d", fork=True), "_faixa": "2000..5000"},  # só duplicata
    ]
    candidatos, descartes, etapas = selecao.limpar_candidatos(brutos)

    assert candidatos["repo"].tolist() == ["a/a"]
    assert candidatos["faixa_estrelas"].tolist() == ["1000..2000"]
    assert {(d.etapa, d.repo) for d in descartes.itertuples()} == {
        ("duplicata", "a/a"), ("duplicata", "d/d"),
        ("fork", "b/b"), ("fork", "d/d"), ("arquivado", "c/c"),
    }
    assert [(e["etapa"], e["entraram"], e["sairam"]) for e in etapas] == [
        ("duplicata", 6, 2), ("fork", 4, 2), ("arquivado", 2, 1),
    ]
    validar(candidatos, SCHEMAS["candidatos"])


@responses.activate
def test_buscar_candidatos_marca_a_faixa_de_origem():
    _busca([_item("a/a")])
    _busca([_item("b/b", 3000)])
    brutos = selecao.buscar_candidatos(["1000..2000", "2000..5000"])
    assert [(b["full_name"], b["_faixa"]) for b in brutos] == [
        ("a/a", "1000..2000"), ("b/b", "2000..5000"),
    ]


# --- filtros ---------------------------------------------------------------

def _mock_repo(nome, workflows=1, releases=5, runs=50, status_404_actions=False):
    if status_404_actions:
        responses.add(responses.GET, f"{API}/repos/{nome}/actions/workflows",
                      status=404, json={})
    else:
        responses.add(responses.GET, f"{API}/repos/{nome}/actions/workflows",
                      json={"total_count": workflows, "workflows": []})
    dentro = [
        {"tag_name": f"v{i}", "published_at": f"2025-0{i + 1}-10T10:00:00Z"}
        for i in range(releases)
    ]
    responses.add(responses.GET, f"{API}/repos/{nome}/releases", json=dentro)
    responses.add(responses.GET, f"{API}/repos/{nome}",
                  json={"default_branch": "main"})
    responses.add(responses.GET, f"{API}/repos/{nome}/actions/runs",
                  json={"total_count": runs, "workflow_runs": []})


@responses.activate
def test_sem_actions_nao_gasta_chamadas_das_etapas_seguintes():
    _mock_repo("a/a", status_404_actions=True)
    aprovados, descartes, funil = filtros.filtrar(["a/a"], _cfg())
    assert aprovados == []
    assert [d["etapa"] for d in descartes] == ["usa_actions"]
    assert len(responses.calls) == 1


@responses.activate
def test_workflows_zerados_tambem_descartam():
    _mock_repo("a/a", workflows=0)
    aprovados, descartes, _ = filtros.filtrar(["a/a"], _cfg())
    assert aprovados == [] and descartes[0]["etapa"] == "usa_actions"


@responses.activate
def test_releases_contam_so_a_janela_e_ignoram_rascunho():
    itens = [
        {"tag_name": "v1", "published_at": "2024-09-30T23:59:59Z"},   # antes
        {"tag_name": "v2", "published_at": "2024-10-01T00:00:00Z"},   # borda
        {"tag_name": "v3", "published_at": "2025-09-30T23:59:59Z"},   # borda
        {"tag_name": "v4", "published_at": "2025-10-01T00:00:00Z"},   # depois
        {"tag_name": "v5", "published_at": "2025-01-01T00:00:00Z", "draft": True},
        {"tag_name": "v6", "published_at": None},
    ]
    responses.add(responses.GET, f"{API}/repos/a/a/releases", json=itens)
    assert filtros.releases_na_janela(
        "a/a", date(2024, 10, 1), date(2025, 9, 30)) == 2


@responses.activate
def test_runs_somam_as_conclusions_e_param_ao_atingir_o_minimo():
    responses.add(responses.GET, f"{API}/repos/a/a", json={"default_branch": "main"})
    responses.add(responses.GET, f"{API}/repos/a/a/actions/runs",
                  json={"total_count": 30, "workflow_runs": []})
    n = filtros.runs_validos("a/a", date(2024, 10, 1), date(2025, 9, 30), 50)
    # 4 conclusions x 30 = 120, mas para na segunda (60 >= 50).
    assert n == 60
    assert len(responses.calls) == 3   # repo + 2 consultas de runs


@responses.activate
def test_erro_de_api_descarta_o_repo_sem_derrubar_a_selecao():
    _mock_repo("ok/ok")
    responses.add(responses.GET, f"{API}/repos/ruim/ruim/actions/workflows",
                  status=451, json={"message": "legal"})
    aprovados, descartes, _ = filtros.filtrar(["ruim/ruim", "ok/ok"], _cfg())
    assert aprovados == ["ok/ok"]
    assert "451" in descartes[0]["motivo"]


@responses.activate
def test_401_derruba_a_selecao():
    from coleta.http import ErroDeHTTP
    responses.add(responses.GET, f"{API}/repos/a/a/actions/workflows",
                  status=401, json={"message": "Bad credentials"})
    with pytest.raises(ErroDeHTTP):
        filtros.filtrar(["a/a"], _cfg())


# --- sorteio ---------------------------------------------------------------

REPOS = [f"o/r{i:02d}" for i in range(10)]


def test_mesma_semente_mesma_amostra_independente_da_ordem():
    a, _, _ = filtros.sortear(REPOS, 4, seed=42)
    b, _, _ = filtros.sortear(list(reversed(REPOS)), 4, seed=42)
    assert a == b and len(a) == 4


def test_semente_diferente_pode_mudar_a_amostra():
    amostras = {tuple(filtros.sortear(REPOS, 4, seed=s)[0]) for s in range(10)}
    assert len(amostras) > 1


def test_menos_aprovados_que_n_repos_leva_todos():
    amostra, descartes, funil = filtros.sortear(REPOS[:3], 10, seed=1)
    assert amostra == REPOS[:3] and descartes == [] and funil["sairam"] == 0


# --- funil -----------------------------------------------------------------

@responses.activate
def test_funil_com_10_repositorios_fake_fecha(tmp_path):
    cfg = _cfg(n_repos=3)
    nomes = [f"o/r{i}" for i in range(10)]
    _busca([_item(n) for n in nomes[:7]]
           + [_item("o/dup")] * 2                       # 1 duplicata
           + [_item("o/fork", fork=True)])
    # 10 itens brutos: 1 duplicata, 1 fork -> 8 candidatos
    for i, n in enumerate(nomes[:7]):
        _mock_repo(
            n,
            status_404_actions=(i == 0),          # r0 sai em usa_actions
            releases=2 if i == 1 else 5,          # r1 sai em min_releases
            runs=10 if i == 2 else 50,            # r2 sai em min_runs
        )
    _mock_repo("o/dup")

    amostra = selecao.selecionar(cfg, tmp_path)

    funil = pd.read_csv(tmp_path / "funil.csv")
    validar(funil, SCHEMAS["funil"])
    assert filtros.funil_fecha(funil, len(amostra))
    assert funil["etapa"].tolist() == [
        "duplicata", "fork", "arquivado", "sem_push_na_janela",
        "nao_examinados", "usa_actions", "min_releases", "min_runs",
    ]
    assert funil["entraram"].tolist()[:5] == [10, 9, 8, 8, 8]
    assert len(amostra) == 3
    # a soma fecha: o que os filtros recebem é o que a seleção examinou
    nao_examinados = int(funil.loc[funil["etapa"] == "nao_examinados", "sairam"].iloc[0])
    assert int(funil.loc[funil["etapa"] == "usa_actions", "entraram"].iloc[0]) == 8 - nao_examinados

    descartes = pd.read_csv(tmp_path / "descartes.csv")
    validar(descartes, SCHEMAS["descartes"])
    # descartes.csv lista só quem foi examinado e barrado, não os não examinados
    assert len(descartes) == funil["sairam"].sum() - nao_examinados
    candidatos = pd.read_csv(tmp_path / "candidatos.csv")
    assert len(candidatos) == 8


def test_funil_que_nao_fecha_e_detectado():
    funil = pd.DataFrame([
        {"etapa": "a", "entraram": 10, "sairam": 2, "motivo": "x"},
        {"etapa": "b", "entraram": 9, "sairam": 1, "motivo": "y"},   # devia ser 8
    ])
    assert not filtros.funil_fecha(funil, 8)


def test_funil_cuja_sobra_nao_e_a_amostra_nao_fecha():
    funil = pd.DataFrame([
        {"etapa": "a", "entraram": 10, "sairam": 2, "motivo": "x"},
    ])
    assert filtros.funil_fecha(funil, 8)
    assert not filtros.funil_fecha(funil, 7)


# --- pré-filtro por pushed_at (Issue #58) ----------------------------------------

INICIO = date(2025, 10, 1)


def _com_push(nome, pushed_at):
    return {**_item(nome, pushed_at=pushed_at), "_faixa": "1000..2000"}


def test_sem_push_na_janela_sai_sem_chamar_a_api():
    brutos = [
        _com_push("p/parado", "2025-09-30T23:59:59Z"),
        _com_push("p/no-limite", "2025-10-01T00:00:00Z"),
        _com_push("p/recente", "2026-03-01T10:00:00Z"),
        {**_item("p/sem-data"), "_faixa": "1000..2000"},      # sem pushed_at: fica
    ]
    candidatos, descartes, etapas = selecao.limpar_candidatos(brutos, janela_inicio=INICIO)
    assert candidatos["repo"].tolist() == ["p/no-limite", "p/recente", "p/sem-data"]
    assert descartes["repo"].tolist() == ["p/parado"]
    assert descartes["etapa"].tolist() == ["sem_push_na_janela"]
    assert "2025-10-01" in descartes["motivo"].iloc[0]
    assert [(e["etapa"], e["entraram"], e["sairam"]) for e in etapas][-1] == (
        "sem_push_na_janela", 4, 1)


def test_sem_janela_o_prefiltro_nao_age():
    brutos = [_com_push("p/parado", "2000-01-01T00:00:00Z")]
    candidatos, _, etapas = selecao.limpar_candidatos(brutos)
    assert candidatos["repo"].tolist() == ["p/parado"]
    assert [e["etapa"] for e in etapas] == ["duplicata", "fork", "arquivado"]


def test_fork_parado_cai_em_fork_e_nao_em_sem_push():
    brutos = [{**_item("p/f", fork=True, pushed_at="2000-01-01T00:00:00Z"),
               "_faixa": "1000..2000"}]
    _, descartes, _ = selecao.limpar_candidatos(brutos, janela_inicio=INICIO)
    assert descartes["etapa"].tolist() == ["fork"]


# --- filtro preguiçoso (Issue #58) ---------------------------------------------------

def test_ordem_de_exame_depende_da_semente_nao_da_ordem_de_entrada():
    a = filtros.ordem_de_exame(REPOS, seed=42)
    b = filtros.ordem_de_exame(list(reversed(REPOS)), seed=42)
    assert a == b and sorted(a) == REPOS
    assert len({tuple(filtros.ordem_de_exame(REPOS, seed=s)) for s in range(8)}) > 1


@responses.activate
def test_para_ao_aprovar_n_repos_e_nao_chama_a_api_para_o_resto():
    for n in REPOS:
        _mock_repo(n)
    esperados = filtros.ordem_de_exame(REPOS, seed=42)[:3]
    aprovados, descartes, funil, nao_examinados = filtros.filtrar_ate(
        REPOS, _cfg(n_repos=3), alvo=3, seed=42)
    assert aprovados == esperados
    assert descartes == [] and nao_examinados == 7
    tocados = {re.search(r"/repos/([^/]+/[^/?]+)", c.request.url).group(1)
               for c in responses.calls}
    assert tocados <= set(esperados)


@responses.activate
def test_funil_dos_filtros_conta_so_os_examinados_e_fecha():
    ordem = filtros.ordem_de_exame(REPOS, seed=42)
    # os 2 primeiros examinados caem em etapas diferentes; os seguintes passam
    _mock_repo(ordem[0], status_404_actions=True)
    _mock_repo(ordem[1], releases=1)
    for n in ordem[2:]:
        _mock_repo(n)
    aprovados, descartes, funil, nao_examinados = filtros.filtrar_ate(
        REPOS, _cfg(n_repos=3), alvo=3, seed=42)
    assert aprovados == ordem[2:5] and nao_examinados == 5
    assert [(f["etapa"], f["entraram"], f["sairam"]) for f in funil] == [
        ("usa_actions", 5, 1), ("min_releases", 4, 1), ("min_runs", 3, 0)]
    assert {d["repo"]: d["etapa"] for d in descartes} == {
        ordem[0]: "usa_actions", ordem[1]: "min_releases"}


@responses.activate
def test_menos_aprovados_que_alvo_examina_todos():
    for n in REPOS[:4]:
        _mock_repo(n)
    aprovados, _, funil, nao_examinados = filtros.filtrar_ate(
        REPOS[:4], _cfg(n_repos=10), alvo=10, seed=1)
    assert sorted(aprovados) == REPOS[:4] and nao_examinados == 0
    assert funil[0]["entraram"] == 4


@responses.activate
def test_erro_de_api_descarta_o_repo_e_o_filtro_segue():
    ordem = filtros.ordem_de_exame(REPOS[:3], seed=3)
    responses.add(responses.GET, f"{API}/repos/{ordem[0]}/actions/workflows", status=451)
    for n in ordem[1:]:
        _mock_repo(n)
    aprovados, descartes, _, _ = filtros.filtrar_ate(
        REPOS[:3], _cfg(n_repos=2), alvo=2, seed=3)
    assert aprovados == ordem[1:]
    assert "451" in descartes[0]["motivo"]


@responses.activate
def test_401_derruba_o_filtro_preguicoso():
    responses.add(responses.GET, f"{API}/repos/o/r00/actions/workflows", status=401,
                  json={"message": "Bad credentials"})
    with pytest.raises(Exception) as e:
        filtros.filtrar_ate(["o/r00"], _cfg(), alvo=1, seed=1)
    assert getattr(e.value, "status", None) == 401


@responses.activate
def test_selecionar_nao_chama_a_api_para_repo_parado(tmp_path):
    _busca([_item("o/vivo", pushed_at="2026-01-01T00:00:00Z"),
            _item("o/parado", pushed_at="2020-01-01T00:00:00Z")])
    _mock_repo("o/vivo")
    _mock_repo("o/parado")
    amostra = selecao.selecionar(_cfg(janela_inicio=date(2025, 1, 1), n_repos=5), tmp_path)
    assert amostra["repo"].tolist() == ["o/vivo"]
    assert not any("o/parado" in c.request.url for c in responses.calls)
    funil = pd.read_csv(tmp_path / "funil.csv")
    assert filtros.funil_fecha(funil, 1)
    assert funil.set_index("etapa").loc["sem_push_na_janela", "sairam"] == 1
