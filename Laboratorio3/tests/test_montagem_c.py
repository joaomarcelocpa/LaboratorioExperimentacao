"""Colunas de CI de metricas.csv e a série de metricas_mensais.csv (#39)."""
import math
from datetime import date

import pandas as pd
import pytest

from metricas.schemas import SCHEMAS, df_vazio, validar
from pipeline.config import Config
from pipeline.montagem import montar_metricas, montar_metricas_mensais

COLUNAS_C = ["cfr_a", "cfr_a_bruto", "cfr_a_sem_flaky", "pct_falhas_flaky",
             "recuperacao_h", "recuperacao_sem_flaky_h", "pct_censurados"]


def _cfg():
    return Config(
        janela_inicio=date(2024, 1, 1), janela_fim=date(2024, 12, 31),
        faixas_estrelas=[], min_releases=5, min_runs=50, n_repos=10, seed=42,
        ambientes_producao=["production"], labels_bug=["bug"], n_dias_issue=7,
        bots=["dependabot[bot]"], _janela_placeholder=False,
    )


def _run(repo, run_id, quando, classe, head_sha=None, workflow_id=1,
         criado_em=None, fim=None):
    conclusion = {"sucesso": "success", "falha": "failure"}[classe]
    return {
        "repo": repo, "run_id": run_id, "workflow_id": workflow_id,
        "workflow_nome": "ci", "event": "push",
        "head_sha": head_sha or f"sha{run_id}", "run_attempt": 1,
        "conclusion": conclusion, "classe": classe,
        "inicio": quando, "fim": fim or quando,
        "criado_em": criado_em or quando,
    }


def _runs(*linhas):
    return pd.DataFrame(list(linhas), columns=list(SCHEMAS["runs"].colunas))


def _vazios():
    return (df_vazio(SCHEMAS["releases"]), df_vazio(SCHEMAS["commits"]),
            df_vazio(SCHEMAS["tags"]), df_vazio(SCHEMAS["deployments"]))


def _montar(repos, runs=None, attempts=None):
    rel, com, tag, dep = _vazios()
    return montar_metricas(repos, rel, com, tag, dep, _cfg(),
                           runs_df=runs, attempts_df=attempts)


def test_cfr_a_duas_falhas_e_oito_sucessos_e_20_por_cento():
    repo = "o/r"
    linhas = [_run(repo, i, f"2024-03-{i + 1:02d}T10:00:00Z", "sucesso") for i in range(8)]
    linhas += [_run(repo, 100 + i, f"2024-04-{i + 1:02d}T10:00:00Z", "falha") for i in range(2)]
    df = _montar([repo], _runs(*linhas))
    assert df.iloc[0]["cfr_a"] == pytest.approx(0.2)


def test_flaky_separa_oficial_bruto_e_sem_flaky():
    repo = "o/r"
    # o run listado é a tentativa 2 (sucesso); a tentativa 1 falhou no mesmo head_sha
    run = _run(repo, 1, "2024-03-01T10:00:00Z", "sucesso", head_sha="aaa")
    run["run_attempt"] = 2
    attempts = pd.DataFrame([{
        "repo": repo, "run_id": 1, "tentativa": 1, "conclusion": "failure",
        "inicio": "2024-03-01T09:00:00Z", "fim": "2024-03-01T09:30:00Z",
    }], columns=list(SCHEMAS["run_attempts"].colunas))
    linha = _montar([repo], _runs(run), attempts).iloc[0]
    assert linha["cfr_a"] == 0.0
    assert linha["cfr_a_bruto"] == pytest.approx(0.5)
    assert linha["cfr_a_sem_flaky"] == 0.0
    assert linha["pct_falhas_flaky"] == 1.0


def test_recuperacao_de_uma_hora_e_vinte():
    repo = "o/r"
    runs = _runs(
        _run(repo, 1, "2024-03-01T09:00:00Z", "sucesso"),
        _run(repo, 2, "2024-03-01T10:00:00Z", "falha"),
        _run(repo, 3, "2024-03-01T11:00:00Z", "sucesso", fim="2024-03-01T11:20:00Z"),
    )
    linha = _montar([repo], runs).iloc[0]
    assert linha["recuperacao_h"] == pytest.approx(4 / 3)
    assert linha["pct_censurados"] == 0.0


def test_falha_nunca_recuperada_e_censurada():
    repo = "o/r"
    runs = _runs(
        _run(repo, 1, "2024-03-01T09:00:00Z", "sucesso"),
        _run(repo, 2, "2024-03-01T10:00:00Z", "falha"),
    )
    linha = _montar([repo], runs).iloc[0]
    assert linha["pct_censurados"] == 1.0
    assert math.isnan(linha["recuperacao_h"])


def test_repo_sem_runs_fica_nan_e_nao_zero():
    linha = _montar(["o/sem-runs"], _runs()).iloc[0]
    assert all(math.isnan(linha[c]) for c in COLUNAS_C)


def test_runs_de_outro_repo_nao_vazam():
    runs = _runs(_run("o/outro", 1, "2024-03-01T10:00:00Z", "falha"),
                 _run("o/outro", 2, "2024-03-02T10:00:00Z", "sucesso"))
    linha = _montar(["o/meu"], runs).iloc[0]
    assert math.isnan(linha["cfr_a"])


def test_colunas_de_ci_nao_quebram_o_contrato():
    repo = "o/r"
    linhas = [_run(repo, i, f"2024-03-{i + 1:02d}T10:00:00Z", "sucesso") for i in range(5)]
    linhas.append(_run(repo, 99, "2024-04-01T10:00:00Z", "falha"))
    df = _montar([repo], _runs(*linhas))
    validar(df, SCHEMAS["metricas"], estrito=False)


def test_mensais_mes_pobre_fica_nan():
    repo = "o/r"
    marco = [_run(repo, i, f"2024-03-{i + 1:02d}T10:00:00Z", "sucesso") for i in range(5)]
    marco.append(_run(repo, 50, "2024-03-20T10:00:00Z", "falha"))
    abril = [_run(repo, 60 + i, f"2024-04-{i + 1:02d}T10:00:00Z", "sucesso") for i in range(3)]
    df = montar_metricas_mensais([repo], _runs(*marco, *abril), _cfg())
    validar(df, SCHEMAS["metricas_mensais"])
    m = df.set_index("mes")
    assert m.loc["2024-03", "runs_validos"] == 6
    assert m.loc["2024-03", "cfr_a"] == pytest.approx(1 / 6)
    assert m.loc["2024-04", "runs_validos"] == 3
    assert math.isnan(m.loc["2024-04", "cfr_a"])
    assert math.isnan(m.loc["2024-04", "recuperacao_h"])


def test_mensais_ignora_repos_fora_da_lista():
    runs = _runs(*[_run("o/fora", i, f"2024-03-{i + 1:02d}T10:00:00Z", "sucesso")
                   for i in range(6)])
    assert montar_metricas_mensais(["o/dentro"], runs, _cfg()).empty


def test_mensais_sem_runs_e_vazio_valido():
    df = montar_metricas_mensais(["o/r"], None, _cfg())
    assert df.empty
    validar(df, SCHEMAS["metricas_mensais"])
