"""Sorteio da amostra-ouro e planilha de conferência (dados inventados)."""
import zipfile

import pandas as pd
import pytest

from conferencia import sorteio


def _repos(n=8):
    return pd.DataFrame({
        "repo": [f"org/r{i:02d}" for i in range(n)],
        "linguagem": "Python",
        "estrelas": 1500,
    })


def _releases(repos, por_repo=7):
    linhas = []
    for r in repos:
        for i in range(por_repo):
            linhas.append({
                "repo": r, "tag": f"v1.0.{i}", "publicada_em": f"2026-0{1 + i}-10T00:00:00Z",
                "prerelease": False, "na_janela": True, "body": f"notas {i}",
            })
        linhas.append({  # pré-release e fora da janela nunca podem ser sorteados
            "repo": r, "tag": "v2.0.0-rc1", "publicada_em": "2026-08-01T00:00:00Z",
            "prerelease": True, "na_janela": True, "body": "rc",
        })
        linhas.append({
            "repo": r, "tag": "v0.0.1", "publicada_em": "2024-01-01T00:00:00Z",
            "prerelease": False, "na_janela": False, "body": "velha",
        })
    return pd.DataFrame(linhas)


def _commits(releases):
    linhas = []
    for repo, tag in zip(releases["repo"], releases["tag"]):
        for k in range(3):
            linhas.append({"repo": repo, "release_tag": tag, "sha": f"{tag}{k}",
                           "mensagem": f"fix: coisa {k}\n\ncorpo longo"})
    return pd.DataFrame(linhas)


@pytest.fixture
def processed(tmp_path):
    repos = _repos()
    rel = _releases(repos["repo"])
    repos.to_csv(tmp_path / "repos.csv", index=False)
    rel.to_csv(tmp_path / "releases.csv", index=False)
    _commits(rel).to_csv(tmp_path / "commits.csv", index=False)
    return tmp_path


def test_sortear_repos_e_reproduzivel_e_respeita_o_tamanho():
    a = sorteio.sortear_repos(_repos(), 5, seed=42)
    b = sorteio.sortear_repos(_repos().sample(frac=1, random_state=1), 5, seed=42)
    assert len(a) == 5
    assert list(a["repo"]) == list(b["repo"])  # a ordem de entrada não importa


def test_sortear_repos_recusa_amostra_menor_que_o_pedido():
    with pytest.raises(ValueError):
        sorteio.sortear_repos(_repos(3), 5, seed=42)


def test_gerar_sorteia_5_releases_validas_por_repo(processed, tmp_path):
    arquivos = sorteio.gerar(processed, tmp_path / "saida", seed=42, n_repos=5)
    ouro = pd.read_csv(arquivos["amostra_ouro"])
    assert ouro["repo"].nunique() == 5
    assert (ouro.groupby("repo").size() == 5).all()
    assert not ouro["tag"].isin(["v2.0.0-rc1", "v0.0.1"]).any()


def test_mesma_seed_gera_arquivos_identicos(processed, tmp_path):
    a = sorteio.gerar(processed, tmp_path / "a", seed=42, n_repos=5)
    b = sorteio.gerar(processed, tmp_path / "b", seed=42, n_repos=5)
    for nome in a:
        assert a[nome].read_bytes() == b[nome].read_bytes()


def test_seed_diferente_muda_as_releases(processed, tmp_path):
    a = sorteio.gerar(processed, tmp_path / "a", seed=42, n_repos=5)
    b = sorteio.gerar(processed, tmp_path / "b", seed=7, n_repos=5)
    assert a["amostra_ouro"].read_bytes() != b["amostra_ouro"].read_bytes()


def test_planilha_tem_perguntas_em_branco_e_nao_mostra_a_heuristica(processed, tmp_path):
    arquivos = sorteio.gerar(processed, tmp_path / "s", seed=42, n_repos=5)
    p_repos = pd.read_csv(arquivos["planilha_repositorios"], dtype=str, keep_default_na=False)
    p_rel = pd.read_csv(arquivos["planilha_releases"], dtype=str, keep_default_na=False)
    assert list(p_repos.columns) == sorteio.COLUNAS_PLANILHA_REPOS
    assert list(p_rel.columns) == sorteio.COLUNAS_PLANILHA_RELEASES
    assert (p_repos["tipo_projeto"] == "").all() and (p_repos["entregas_reais"] == "").all()
    assert (p_rel["corretiva"] == "").all()
    colunas = " ".join(p_repos.columns) + " " + " ".join(p_rel.columns)
    assert "cfr" not in colunas and "heuristica" not in colunas


def test_planilha_traz_link_notas_e_mensagens_de_commit(processed, tmp_path):
    arquivos = sorteio.gerar(processed, tmp_path / "s", seed=42, n_repos=5)
    p_rel = pd.read_csv(arquivos["planilha_releases"], dtype=str, keep_default_na=False)
    linha = p_rel.iloc[0]
    assert linha["link"] == f"https://github.com/{linha['repo']}/releases/tag/{linha['tag']}"
    assert linha["notas"].startswith("notas")
    assert "- fix: coisa 0" in linha["commits"]
    assert "corpo longo" not in linha["commits"]  # só a primeira linha


def test_link_codifica_tag_de_monorepo():
    assert sorteio.link_release("o/r", "pkg/a#1.0") == (
        "https://github.com/o/r/releases/tag/pkg%2Fa%231.0"
    )


def test_formatar_commits_corta_lista_longa():
    texto = sorteio.formatar_commits([f"m{i}" for i in range(sorteio.MAX_COMMITS + 7)])
    assert texto.endswith("(e mais 7 commits)")


def test_le_commits_zipado_ignorando_lixo_macosx(processed, tmp_path):
    csv = processed / "commits.csv"
    zpath = processed / "commits.csv.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(csv, "commits.csv")
        zf.writestr("__MACOSX/._commits.csv", b"lixo")
    csv.unlink()
    arquivos = sorteio.gerar(processed, tmp_path / "s", seed=42, n_repos=5)
    assert len(pd.read_csv(arquivos["amostra_ouro"])) == 25


def test_release_sem_commits_nao_e_sorteada(processed, tmp_path):
    commits = pd.read_csv(processed / "commits.csv")
    commits = commits[commits["release_tag"] != "v1.0.0"]
    commits.to_csv(processed / "commits.csv", index=False)
    arquivos = sorteio.gerar(processed, tmp_path / "s", seed=42, n_repos=5)
    assert "v1.0.0" not in set(pd.read_csv(arquivos["amostra_ouro"])["tag"])
