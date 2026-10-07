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


def _item(nome, estrelas=1500, fork=False, archived=False):
    return {"full_name": nome, "stargazers_count": estrelas,
            "fork": fork, "archived": archived}


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
    # (7 + o/dup + o/fork removido = 8)
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
        "duplicata", "fork", "arquivado",
        "usa_actions", "min_releases", "min_runs", "sorteio",
    ]
    # 10 brutos -> 9 -> 8 -> 8 -> 7 -> 6 -> 5 -> 3 sorteados
    assert funil["entraram"].tolist() == [10, 9, 8, 8, 7, 6, 5]
    assert funil["sairam"].tolist() == [1, 1, 0, 1, 1, 1, 2]
    assert len(amostra) == 3

    descartes = pd.read_csv(tmp_path / "descartes.csv")
    validar(descartes, SCHEMAS["descartes"])
    assert len(descartes) == funil["sairam"].sum()
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
