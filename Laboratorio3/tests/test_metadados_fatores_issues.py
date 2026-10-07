"""Metadados, fatores e issues de bug (Issue #44). Sem rede."""
import base64
import math
from datetime import date

import pandas as pd
import pytest
import responses

from coleta import fatores, issues, metadados
from coleta.cache import Cache
from coleta.http import Cliente, redefinir_cliente
from metricas.schemas import SCHEMAS, validar
from pipeline.config import Config

API = "https://api.github.com"


@pytest.fixture(autouse=True)
def cliente_sem_rede(tmp_path):
    redefinir_cliente(Cliente(token="tok", cache=Cache(tmp_path / "c.sqlite"),
                              agora=lambda: 1000.0, dormir=lambda s: None))
    yield
    redefinir_cliente(None)


def _cfg():
    return Config(
        janela_inicio=date(2024, 10, 1), janela_fim=date(2025, 9, 30),
        faixas_estrelas=[], min_releases=5, min_runs=50, n_repos=3, seed=1,
        ambientes_producao=[], labels_bug=["bug", "regression"],
        n_dias_issue=7, bots=[], _janela_placeholder=False,
    )


# --- contribuidores ---------------------------------------------------------

@responses.activate
def test_contribuidores_vem_da_ultima_pagina_do_link():
    responses.add(
        responses.GET, f"{API}/repos/a/a/contributors", json=[{"login": "x"}],
        headers={"Link": f'<{API}/repos/a/a/contributors?per_page=1&anon=true&page=2>; '
                         f'rel="next", <{API}/repos/a/a/contributors?per_page=1&anon=true'
                         f'&page=1234>; rel="last"'},
    )
    assert metadados.contar_contribuidores("a/a") == 1234


@responses.activate
def test_contribuidores_sem_link_e_o_tamanho_da_lista():
    responses.add(responses.GET, f"{API}/repos/a/a/contributors", json=[{"login": "x"}])
    assert metadados.contar_contribuidores("a/a") == 1


@responses.activate
def test_contribuidores_sem_link_e_lista_vazia_da_zero():
    responses.add(responses.GET, f"{API}/repos/a/a/contributors", json=[])
    assert metadados.contar_contribuidores("a/a") == 0


@responses.activate
def test_contribuidores_recusado_pela_api_e_nulo_e_nao_zero():
    responses.add(responses.GET, f"{API}/repos/a/a/contributors", status=403,
                  json={"message": "The history or contributor list is too large"})
    assert metadados.contar_contribuidores("a/a") is None


@responses.activate
def test_link_last_sem_numero_de_pagina_e_erro():
    responses.add(responses.GET, f"{API}/repos/a/a/contributors", json=[{}],
                  headers={"Link": f'<{API}/x>; rel="last"'})
    with pytest.raises(ValueError):
        metadados.contar_contribuidores("a/a")


# --- organização e idade ----------------------------------------------------

@responses.activate
def test_org_verificada():
    responses.add(responses.GET, f"{API}/orgs/o", json={"is_verified": True})
    assert metadados.org_verificada("o", "Organization") is True


def test_usuario_nunca_e_verificado_e_nao_gasta_chamada():
    assert metadados.org_verificada("u", "User") is False


@responses.activate
def test_org_sumida_nao_e_verificada():
    responses.add(responses.GET, f"{API}/orgs/o", status=404, json={})
    assert metadados.org_verificada("o", "Organization") is False


def test_idade_e_medida_ate_o_fim_da_janela():
    anos = metadados.idade_em_anos("2020-09-30T00:00:00Z", date(2025, 9, 30))
    assert anos == pytest.approx(5.0, abs=0.01)


# --- automação de release ---------------------------------------------------

@pytest.mark.parametrize("raiz, esperado", [
    ([".releaserc"], {"semantic-release"}),
    ([".releaserc.json", "README.md"], {"semantic-release"}),
    (["release-please-config.json"], {"release-please"}),
    ([".changeset"], {"changesets"}),
    ([".goreleaser.yml"], {"goreleaser"}),
    ([".goreleaser.yaml"], {"goreleaser"}),
    (["README.md", "src", "Makefile"], set()),
    (["releaserc"], set()),                      # sem o ponto não é o arquivo
    ([".changesets"], set()),                    # nome quase igual
    ([".releaserc", ".goreleaser.yml"], {"semantic-release", "goreleaser"}),
])
def test_ferramenta_por_arquivos(raiz, esperado):
    assert fatores.ferramenta_por_arquivos(raiz) == esperado


def test_ferramenta_por_texto_de_workflow():
    yaml_ = "steps:\n  - uses: googleapis/release-please-action@v4\n"
    assert fatores.ferramenta_por_texto([yaml_]) == {"release-please"}
    assert fatores.ferramenta_por_texto(["run: npx semantic-release"]) == {"semantic-release"}
    assert fatores.ferramenta_por_texto(["uses: changesets/action@v1"]) == {"changesets"}
    assert fatores.ferramenta_por_texto(["uses: goreleaser/goreleaser-action"]) == {"goreleaser"}


def test_gh_release_create_nao_e_automacao():
    assert fatores.ferramenta_por_texto(["run: gh release create v1"]) == set()


def _conteudo(nome, path, texto):
    return {"name": nome, "path": path, "type": "file",
            "encoding": "base64",
            "content": base64.b64encode(texto.encode()).decode()}


def _arvore(raiz, workflows=None, textos=None):
    responses.add(responses.GET, f"{API}/repos/a/a/contents/",
                  json=[{"name": n, "type": "file"} for n in raiz])
    if workflows is None:
        responses.add(responses.GET, f"{API}/repos/a/a/contents/.github/workflows",
                      status=404, json={})
        return
    responses.add(
        responses.GET, f"{API}/repos/a/a/contents/.github/workflows",
        json=[{"name": n, "path": f".github/workflows/{n}", "type": "file"}
              for n in workflows],
    )
    for n in workflows:
        responses.add(
            responses.GET, f"{API}/repos/a/a/contents/.github/workflows/{n}",
            json=_conteudo(n, f".github/workflows/{n}", textos[n]),
        )


@responses.activate
def test_automacao_por_arquivo_nao_le_workflows_se_nao_precisa():
    _arvore([".releaserc"])
    assert fatores.automacao_release("a/a", "main") == (True, "semantic-release")


@responses.activate
def test_automacao_so_por_mencao_no_workflow():
    _arvore(["README.md"], ["release.yml", "ci.yml"],
            {"release.yml": "uses: googleapis/release-please-action@v4",
             "ci.yml": "run: pytest"})
    assert fatores.automacao_release("a/a", "main") == (True, "release-please")


@responses.activate
def test_sem_automacao():
    _arvore(["README.md"], ["ci.yml"], {"ci.yml": "run: pytest"})
    assert fatores.automacao_release("a/a", "main") == (False, "nenhuma")


@responses.activate
def test_repo_sem_pasta_de_workflows():
    _arvore(["README.md"])
    assert fatores.automacao_release("a/a", "main") == (False, "nenhuma")


@responses.activate
def test_arquivo_vence_a_mencao_quando_divergem():
    _arvore([".goreleaser.yml"], ["r.yml"], {"r.yml": "run: npx semantic-release"})
    assert fatores.automacao_release("a/a", "main") == (True, "goreleaser")


# --- Conventional Commits ---------------------------------------------------

ROTULADAS = [
    ("feat: adiciona login", True),
    ("fix(api): corrige timeout", True),
    ("feat!: remove endpoint antigo", True),
    ("refactor(core)!: troca o parser", True),
    ("Fix: maiúscula também vale", True),
    ("Merge pull request #12 from x/y", False),
    ("update readme", False),
    ("feat adiciona sem dois pontos", False),
    ("feat:sem espaço depois", False),
    ("wip: tipo que não existe", False),
]


@pytest.mark.parametrize("mensagem, esperado", ROTULADAS)
def test_regex_de_conventional_commits(mensagem, esperado):
    assert fatores.e_conventional(mensagem) is esperado


def test_so_a_primeira_linha_conta():
    assert fatores.e_conventional("feat: ok\n\nBREAKING CHANGE: x")
    assert not fatores.e_conventional("ajuste\n\nfeat: na segunda linha")


@pytest.mark.parametrize("vazia", [None, "", "   ", math.nan])
def test_mensagem_vazia_nao_e_conventional(vazia):
    assert fatores.e_conventional(vazia) is False


def test_pct_conventional_conta_cada_sha_uma_vez():
    df = pd.DataFrame({
        "sha": ["1", "1", "2", "3"],
        "mensagem": ["feat: a", "feat: a", "ajuste", "fix: b"],
    })
    assert fatores.pct_conventional(df) == pytest.approx(2 / 3)


def test_pct_conventional_dos_dez_rotulados():
    df = pd.DataFrame({"sha": [str(i) for i in range(10)],
                       "mensagem": [m for m, _ in ROTULADAS]})
    assert fatores.pct_conventional(df) == 0.5


def test_pct_conventional_sem_commits_e_nan():
    assert math.isnan(fatores.pct_conventional(pd.DataFrame(columns=["sha", "mensagem"])))


# --- issues de bug ----------------------------------------------------------

def _issue(numero, titulo="quebrou", corpo="", labels=("bug",), pr=False):
    item = {"number": numero, "title": titulo, "body": corpo,
            "created_at": "2025-01-05T10:00:00Z",
            "labels": [{"name": n} for n in labels]}
    if pr:
        item["pull_request"] = {"url": "x"}
    return item


@responses.activate
def test_pr_fica_de_fora_e_issue_com_dois_labels_aparece_uma_vez():
    responses.add(responses.GET, f"{API}/repos/a/a/issues", json=[
        _issue(1, labels=("bug", "regression")), _issue(2, pr=True)])
    responses.add(responses.GET, f"{API}/repos/a/a/issues", json=[
        _issue(1, labels=("bug", "regression")), _issue(3, labels=("regression",))])

    linhas = issues.coletar_issues_bug(
        "a/a", ["bug", "regression"], date(2024, 10, 1), ["v1.0.0"])

    assert [l["numero"] for l in linhas] == [1, 3]
    assert linhas[0]["labels"] == "bug;regression"
    df = issues.df_issues_bug(linhas)
    validar(df, SCHEMAS["issues_bug"])


@responses.activate
def test_consulta_usa_state_all_labels_e_since():
    responses.add(responses.GET, f"{API}/repos/a/a/issues", json=[])
    issues.coletar_issues_bug("a/a", ["type: bug"], date(2024, 10, 1), [])
    url = responses.calls[0].request.url
    assert "state=all" in url and "labels=type%3A+bug" in url.replace("%20", "+")
    assert "since=2024-10-01T00%3A00%3A00Z" in url


@responses.activate
def test_issues_desligadas_dao_lista_vazia():
    responses.add(responses.GET, f"{API}/repos/a/a/issues", status=410,
                  json={"message": "Issues are disabled for this repo"})
    assert issues.coletar_issues_bug("a/a", ["bug"], date(2024, 10, 1), []) == []


def test_df_vazio_respeita_o_contrato():
    df = issues.df_issues_bug([])
    assert df.empty and list(df.columns) == list(SCHEMAS["issues_bug"].colunas)


@pytest.mark.parametrize("texto, tags, esperado", [
    ("quebrou na v1.2.3", ["v1.2.3"], True),
    ("quebrou na 1.2.3", ["v1.2.3"], True),            # sem o v
    ("quebrou na v1.2.3.", ["v1.2.3"], True),          # ponto final de frase
    ("quebrou na v1.2.30", ["v1.2.3"], False),         # prefixo de outra tag
    ("quebrou na v1.2.3.1", ["v1.2.3"], False),
    ("quebrou na v1.2", ["v1.2.3"], False),
    ("quebrou na xv1.2.3", ["v1.2.3"], False),
    ("quebrou ontem", ["v1.2.3"], False),
    ("quebrou na V1.2.3", ["v1.2.3"], True),
    ("quebrou", [], False),
    ("quebrou na v1.2.3", [""], False),
    ("release-2024.1 falhou", ["release-2024.1"], True),
])
def test_cita_tag(texto, tags, esperado):
    assert issues.cita_alguma_tag(texto, None, tags) is esperado


def test_cita_tag_no_corpo():
    assert issues.cita_alguma_tag("erro", "começou depois do v2.0.0", ["v2.0.0"])


# --- repos.csv --------------------------------------------------------------

def _mock_repo_completo(nome="o/r"):
    responses.add(responses.GET, f"{API}/repos/{nome}", json={
        "stargazers_count": 1500, "language": "Python",
        "created_at": "2020-01-01T00:00:00Z", "default_branch": "main",
        "owner": {"login": "o", "type": "Organization"}})
    responses.add(responses.GET, f"{API}/repos/{nome}/contributors", json=[{}],
                  headers={"Link": f'<{API}/x?page=40>; rel="last"'})
    responses.add(responses.GET, f"{API}/orgs/o", json={"is_verified": True})
    responses.add(responses.GET, f"{API}/repos/{nome}/contents/",
                  json=[{"name": ".releaserc", "type": "file"}])
    responses.add(responses.GET, f"{API}/repos/{nome}/contents/.github/workflows",
                  status=404, json={})


@responses.activate
def test_repos_csv_completo_no_contrato():
    _mock_repo_completo()
    commits = pd.DataFrame({"repo": ["o/r", "o/r", "outro/x"],
                            "sha": ["1", "2", "3"],
                            "mensagem": ["feat: a", "ajuste", "feat: b"]})
    df = metadados.coletar_repos(["o/r"], _cfg(), commits)

    validar(df, SCHEMAS["repos"])
    linha = df.iloc[0]
    assert linha["contribuidores"] == 40
    assert bool(linha["org_verificada"]) and bool(linha["automacao_release"])
    assert linha["ferramenta_release"] == "semantic-release"
    assert linha["pct_conventional"] == 0.5    # só os commits do próprio repo
    assert linha["idade_anos"] == pytest.approx(5.75, abs=0.01)


@responses.activate
def test_repo_que_sumiu_fica_de_fora_sem_derrubar_os_outros():
    responses.add(responses.GET, f"{API}/repos/sumiu/x", status=404, json={})
    _mock_repo_completo()
    commits = pd.DataFrame(columns=["repo", "sha", "mensagem"])
    df = metadados.coletar_repos(["sumiu/x", "o/r"], _cfg(), commits)
    assert df["repo"].tolist() == ["o/r"]
    assert math.isnan(df.iloc[0]["pct_conventional"])
