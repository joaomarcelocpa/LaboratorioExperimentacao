"""Séries mensais de CFR e recuperação (RQ 08b)."""
import pandas as pd
import pytest

from metricas.mensais import series_mensais
from metricas.schemas import SCHEMAS, validar


def _run(run_id, classe, mes=10, dia=1, hora=10, fim_hora=None,
         workflow_id=1, head_sha="aaa"):
    fim_hora = hora if fim_hora is None else fim_hora
    carimbo = f"2024-{mes:02d}-{dia:02d}T{hora:02d}:00:00Z"
    return {
        "repo": "o/r", "run_id": run_id, "workflow_id": workflow_id,
        "workflow_nome": "CI", "event": "push", "head_sha": head_sha,
        "run_attempt": 1, "conclusion": "x", "classe": classe,
        "inicio": carimbo,
        "fim": f"2024-{mes:02d}-{dia:02d}T{fim_hora:02d}:00:00Z",
        "criado_em": carimbo,
    }


def _muitos(mes, n, classe="sucesso", inicio_id=0):
    return [_run(inicio_id + i, classe, mes=mes, dia=(i % 28) + 1)
            for i in range(n)]


def test_mes_com_poucos_runs_vira_nan():
    runs = pd.DataFrame(_muitos(10, 4))

    linha = series_mensais(runs, None, min_runs_mes=5).iloc[0]

    assert linha["runs_validos"] == 4
    assert pd.isna(linha["cfr_a"])
    assert pd.isna(linha["recuperacao_h"])


def test_mes_exatamente_no_corte_nao_vira_nan():
    runs = pd.DataFrame(_muitos(10, 5))

    linha = series_mensais(runs, None, min_runs_mes=5).iloc[0]

    assert linha["runs_validos"] == 5
    assert linha["cfr_a"] == pytest.approx(0.0)


def test_corte_configuravel_acima_de_cinco():
    runs = pd.DataFrame(_muitos(10, 7))

    linha = series_mensais(runs, None, min_runs_mes=8).iloc[0]

    assert pd.isna(linha["cfr_a"]), "7 runs com corte 8 vira NaN"


def test_ignorados_nao_contam_em_runs_validos():
    runs = pd.DataFrame(_muitos(10, 5) + _muitos(10, 3, "ignorado", inicio_id=100))

    assert series_mensais(runs, None, min_runs_mes=5).iloc[0]["runs_validos"] == 5


def test_mes_sai_de_criado_em():
    # O critério da janela é a data de criação do run.
    runs = pd.DataFrame(_muitos(11, 5))

    assert series_mensais(runs, None, min_runs_mes=5).iloc[0]["mes"] == "2024-11"


def test_meses_diferentes_viram_linhas_diferentes():
    runs = pd.DataFrame(_muitos(10, 5) + _muitos(11, 5, inicio_id=100))

    df = series_mensais(runs, None, min_runs_mes=5)

    assert list(df["mes"]) == ["2024-10", "2024-11"]


def test_episodio_cai_no_mes_da_primeira_falha():
    # O episódio começa em outubro e termina em novembro: conta em outubro.
    runs = pd.DataFrame(
        _muitos(10, 5)
        + [_run(200, "falha", mes=10, dia=31, hora=23),
           _run(201, "sucesso", mes=11, dia=1, hora=1, fim_hora=1)]
        + _muitos(11, 5, inicio_id=300)
    )

    df = series_mensais(runs, None, min_runs_mes=5).set_index("mes")

    assert df.loc["2024-10", "recuperacao_h"] == pytest.approx(2.0)
    assert pd.isna(df.loc["2024-11", "recuperacao_h"]), \
        "novembro não teve episódio próprio"


def test_mes_com_runs_suficientes_e_sem_falha_tem_cfr_zero_e_recuperacao_nan():
    # São coisas diferentes: o CFR mede 0% de falhas; a recuperação não tem
    # episódio nenhum para medir. A regra do contrato permite.
    runs = pd.DataFrame(_muitos(10, 6))

    linha = series_mensais(runs, None, min_runs_mes=5).iloc[0]

    assert linha["cfr_a"] == pytest.approx(0.0)
    assert pd.isna(linha["recuperacao_h"])


def test_respeita_o_contrato_incluindo_a_regra_do_mes_pobre():
    runs = pd.DataFrame(_muitos(10, 4) + _muitos(11, 6, inicio_id=100))

    df = series_mensais(runs, None, min_runs_mes=5)

    validar(df, SCHEMAS["metricas_mensais"])
    assert list(df.columns) == list(SCHEMAS["metricas_mensais"].colunas)


def test_sem_runs_devolve_frame_vazio_valido():
    df = series_mensais(pd.DataFrame(columns=["repo", "classe"]), None)

    validar(df, SCHEMAS["metricas_mensais"])
    assert df.empty
