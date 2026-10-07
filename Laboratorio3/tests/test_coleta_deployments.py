from datetime import date
import responses
import requests
from pipeline.config import Config
from coleta.deployments import coletar_deployments

BASE = "https://api.github.com"


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1),
        janela_fim=date(2024, 12, 31),
        faixas_estrelas=[],
        min_releases=5, min_runs=50, n_repos=10, seed=42,
        ambientes_producao=["production", "prod"],
        labels_bug=["bug"],
        n_dias_issue=7,
        bots=[],
        _janela_placeholder=False,
    )


@responses.activate
def test_repo_sem_environments_faz_uma_chamada():
    cfg = _cfg()
    responses.add(responses.GET, f"{BASE}/repos/org/repo/environments",
                  json={"environments": []}, status=200)

    session = requests.Session()
    df = coletar_deployments("org/repo", cfg, session)

    assert df.empty
    assert len(responses.calls) == 1


@responses.activate
def test_deployment_com_sucesso():
    cfg = _cfg()
    responses.add(responses.GET, f"{BASE}/repos/org/repo/environments",
                  json={"environments": [{"name": "production"}]}, status=200)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments",
                  json=[{"id": 1, "environment": "production",
                         "created_at": "2024-06-01T10:00:00Z",
                         "sha": "abc"}],
                  headers={"Link": ""}, status=200,
                  match_querystring=False)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments/1/statuses",
                  json=[{"state": "success"}], status=200)

    session = requests.Session()
    df = coletar_deployments("org/repo", cfg, session)

    assert len(df) == 1
    assert df.iloc[0]["estado_final"] == "success"
    assert df.iloc[0]["environment"] == "production"


@responses.activate
def test_ambiente_nao_producao_ignorado():
    cfg = _cfg()
    responses.add(responses.GET, f"{BASE}/repos/org/repo/environments",
                  json={"environments": [{"name": "staging"},
                                          {"name": "production"}]},
                  status=200)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments",
                  json=[{"id": 2, "environment": "production",
                         "created_at": "2024-06-01T10:00:00Z",
                         "sha": "def"}],
                  headers={"Link": ""}, status=200,
                  match_querystring=False)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments/2/statuses",
                  json=[{"state": "failure"}], status=200)

    session = requests.Session()
    df = coletar_deployments("org/repo", cfg, session)

    envs = df["environment"].tolist()
    assert "staging" not in envs
    assert "production" in envs


@responses.activate
def test_deployment_sem_status_tem_estado_desconhecido():
    cfg = _cfg()
    responses.add(responses.GET, f"{BASE}/repos/org/repo/environments",
                  json={"environments": [{"name": "production"}]}, status=200)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments",
                  json=[{"id": 3, "environment": "production",
                         "created_at": "2024-06-01T10:00:00Z", "sha": "ghi"}],
                  headers={"Link": ""}, status=200,
                  match_querystring=False)
    responses.add(responses.GET, f"{BASE}/repos/org/repo/deployments/3/statuses",
                  json=[], status=200)

    session = requests.Session()
    df = coletar_deployments("org/repo", cfg, session)
    assert df.iloc[0]["estado_final"] == "desconhecido"
