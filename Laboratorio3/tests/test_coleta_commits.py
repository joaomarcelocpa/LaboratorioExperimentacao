from datetime import date
import responses
import requests
import pandas as pd
from pipeline.config import Config
from coleta.commits import coletar_commits

BASE = "https://api.github.com"


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1),
        janela_fim=date(2024, 12, 31),
        faixas_estrelas=[],
        min_releases=5, min_runs=50, n_repos=10, seed=42,
        ambientes_producao=["production"],
        labels_bug=["bug"],
        n_dias_issue=7,
        bots=["dependabot[bot]"],
        _janela_placeholder=False,
    )


def _releases_df(tags_e_datas: list[tuple[str, str, bool]]) -> pd.DataFrame:
    return pd.DataFrame([
        {"repo": "org/repo", "tag": tag, "publicada_em": pub, "na_janela": na,
         "prerelease": False, "body": ""}
        for tag, pub, na in tags_e_datas
    ])


@responses.activate
def test_commits_paginados_alem_de_250():
    cfg = _cfg()
    releases = _releases_df([
        ("v1.0.0", "2023-12-01T00:00:00Z", False),
        ("v1.1.0", "2024-03-01T00:00:00Z", True),
    ])
    page2 = f"{BASE}/repos/org/repo/compare/v1.0.0...v1.1.0?page=2"
    page3 = f"{BASE}/repos/org/repo/compare/v1.0.0...v1.1.0?page=3"

    def _commit(sha):
        return {"sha": sha, "commit": {"author": {"date": "2024-02-01T10:00:00Z",
                                                    "email": "a@b.com"},
                                        "message": "feat: algo"},
                "author": {"login": "dev1"}}

    responses.add(responses.GET, f"{BASE}/repos/org/repo/compare/v1.0.0...v1.1.0",
                  json={"commits": [_commit(f"sha{i}") for i in range(250)]},
                  headers={"Link": f'<{page2}>; rel="next"'}, status=200)
    responses.add(responses.GET, page2,
                  json={"commits": [_commit(f"sha{i}") for i in range(250, 400)]},
                  headers={"Link": f'<{page3}>; rel="next"'}, status=200)
    responses.add(responses.GET, page3,
                  json={"commits": [_commit(f"sha{i}") for i in range(400, 450)]},
                  headers={"Link": ""}, status=200)

    session = requests.Session()
    commits_df, ignoradas_df = coletar_commits("org/repo", releases, cfg, session)
    assert len(commits_df) == 450
    assert ignoradas_df.empty


@responses.activate
def test_404_no_compare_vai_para_ignoradas():
    cfg = _cfg()
    releases = _releases_df([
        ("v1.0.0", "2023-12-01T00:00:00Z", False),
        ("v1.1.0", "2024-03-01T00:00:00Z", True),
    ])
    responses.add(responses.GET, f"{BASE}/repos/org/repo/compare/v1.0.0...v1.1.0",
                  status=404, json={"message": "Not Found"})

    session = requests.Session()
    commits_df, ignoradas_df = coletar_commits("org/repo", releases, cfg, session)
    assert commits_df.empty
    assert len(ignoradas_df) == 1
    assert ignoradas_df.iloc[0]["tag"] == "v1.1.0"
    assert "404" in ignoradas_df.iloc[0]["motivo"].lower()


def test_primeira_release_sem_anterior_vai_para_ignoradas():
    cfg = _cfg()
    releases = _releases_df([
        ("v1.0.0", "2024-03-01T00:00:00Z", True),
    ])
    session = requests.Session()
    commits_df, ignoradas_df = coletar_commits("org/repo", releases, cfg, session)
    assert commits_df.empty
    assert len(ignoradas_df) == 1
    assert "sem release anterior" in ignoradas_df.iloc[0]["motivo"].lower()


@responses.activate
def test_eh_bot_marcado_por_login():
    cfg = _cfg()
    releases = _releases_df([
        ("v1.0.0", "2023-12-01T00:00:00Z", False),
        ("v1.1.0", "2024-03-01T00:00:00Z", True),
    ])

    def _commit(sha, login):
        return {"sha": sha,
                "commit": {"author": {"date": "2024-02-01T10:00:00Z",
                                       "email": "x@y.com"},
                            "message": "chore: bump"},
                "author": {"login": login}}

    responses.add(responses.GET, f"{BASE}/repos/org/repo/compare/v1.0.0...v1.1.0",
                  json={"commits": [_commit("sha1", "devhuman"),
                                    _commit("sha2", "dependabot[bot]")]},
                  headers={"Link": ""}, status=200)

    session = requests.Session()
    commits_df, _ = coletar_commits("org/repo", releases, cfg, session)
    assert not commits_df[commits_df["sha"] == "sha1"].iloc[0]["eh_bot"]
    assert commits_df[commits_df["sha"] == "sha2"].iloc[0]["eh_bot"]
