from datetime import date
import responses
import requests
from pipeline.config import Config
from coleta.releases import coletar_releases

BASE = "https://api.github.com"


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1),
        janela_fim=date(2024, 12, 31),
        faixas_estrelas=[],
        min_releases=5,
        min_runs=50,
        n_repos=10,
        seed=42,
        ambientes_producao=["production"],
        labels_bug=["bug"],
        n_dias_issue=7,
        bots=["dependabot[bot]"],
        _janela_placeholder=False,
    )


@responses.activate
def test_draft_excluido_e_prerelease_como_flag():
    cfg = _cfg()
    responses.add(
        responses.GET,
        f"{BASE}/repos/org/repo/releases",
        json=[
            {"tag_name": "v1.0.0", "published_at": "2024-06-01T10:00:00Z",
             "draft": False, "prerelease": False, "body": "GA"},
            {"tag_name": "v1.0.0-rc1", "published_at": "2024-05-30T10:00:00Z",
             "draft": False, "prerelease": True, "body": "RC"},
            {"tag_name": "v0.9.0-draft", "published_at": "2024-05-01T10:00:00Z",
             "draft": True, "prerelease": False, "body": "Draft"},
        ],
        headers={"Link": ""},
        status=200,
    )
    responses.add(responses.GET, f"{BASE}/repos/org/repo/tags",
                  json=[], headers={"Link": ""}, status=200)

    session = requests.Session()
    releases_df, tags_df = coletar_releases("org/repo", cfg, session)

    assert "v0.9.0-draft" not in releases_df["tag"].values, "draft deve ser excluído"
    v1 = releases_df[releases_df["tag"] == "v1.0.0"].iloc[0]
    assert v1["prerelease"] == False
    rc = releases_df[releases_df["tag"] == "v1.0.0-rc1"].iloc[0]
    assert rc["prerelease"] == True


@responses.activate
def test_release_fora_da_janela_mas_incluida_como_anterior():
    cfg = _cfg()  # janela: 2024-01-01 a 2024-12-31
    responses.add(
        responses.GET,
        f"{BASE}/repos/org/repo/releases",
        json=[
            {"tag_name": "v2.0.0", "published_at": "2024-03-01T10:00:00Z",
             "draft": False, "prerelease": False, "body": ""},
            {"tag_name": "v1.0.0", "published_at": "2023-12-01T10:00:00Z",
             "draft": False, "prerelease": False, "body": ""},
            {"tag_name": "v0.9.0", "published_at": "2023-06-01T10:00:00Z",
             "draft": False, "prerelease": False, "body": ""},
        ],
        headers={"Link": ""},
        status=200,
    )
    responses.add(responses.GET, f"{BASE}/repos/org/repo/tags",
                  json=[], headers={"Link": ""}, status=200)

    session = requests.Session()
    releases_df, _ = coletar_releases("org/repo", cfg, session)

    na_janela = releases_df[releases_df["na_janela"]]
    fora = releases_df[~releases_df["na_janela"]]
    assert "v2.0.0" in na_janela["tag"].values
    assert "v1.0.0" in fora["tag"].values
    assert "v0.9.0" not in releases_df["tag"].values


@responses.activate
def test_paginacao_releases():
    cfg = _cfg()
    page2_url = f"{BASE}/repos/org/repo/releases?page=2"
    responses.add(
        responses.GET,
        f"{BASE}/repos/org/repo/releases",
        json=[{"tag_name": "v2.0.0", "published_at": "2024-06-01T10:00:00Z",
               "draft": False, "prerelease": False, "body": ""}],
        headers={"Link": f'<{page2_url}>; rel="next"'},
        status=200,
    )
    responses.add(
        responses.GET,
        page2_url,
        json=[{"tag_name": "v1.0.0", "published_at": "2023-12-01T10:00:00Z",
               "draft": False, "prerelease": False, "body": ""}],
        headers={"Link": ""},
        status=200,
    )
    responses.add(responses.GET, f"{BASE}/repos/org/repo/tags",
                  json=[], headers={"Link": ""}, status=200)

    session = requests.Session()
    releases_df, _ = coletar_releases("org/repo", cfg, session)
    assert set(releases_df["tag"].values) >= {"v2.0.0", "v1.0.0"}


@responses.activate
def test_tags_data_via_commit():
    cfg = _cfg()
    responses.add(responses.GET, f"{BASE}/repos/org/repo/releases",
                  json=[], headers={"Link": ""}, status=200)
    responses.add(
        responses.GET,
        f"{BASE}/repos/org/repo/tags",
        json=[{"name": "v1.0.0", "commit": {"sha": "abc123"}}],
        headers={"Link": ""},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/repos/org/repo/commits/abc123",
        json={"commit": {"author": {"date": "2024-05-15T08:00:00Z"}}},
        status=200,
    )

    session = requests.Session()
    _, tags_df = coletar_releases("org/repo", cfg, session)

    assert len(tags_df) == 1
    row = tags_df.iloc[0]
    assert row["tag"] == "v1.0.0"
    assert row["sha"] == "abc123"
    assert "2024-05-15" in row["data_commit"]
