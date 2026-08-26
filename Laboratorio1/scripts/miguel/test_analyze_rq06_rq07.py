"""Testes das funções de cálculo (RQ06/RQ07) usadas para gerar os gráficos finais."""
import pandas as pd

from analyze_rq06_rq07 import (
    COLS,
    ISSUES_ABERTAS_COL,
    SEM_LINGUAGEM,
    calcular_rq06,
    calcular_rq07,
    calcular_rq07_teste_hipotese,
)

C = COLS


def _linha(**overrides):
    linha = {
        C["primaryLanguage"]: "Python",
        C["closedIssues"]: 5,
        ISSUES_ABERTAS_COL: 5,
        C["mergedPRs"]: 10,
        C["releasesCount"]: 2,
        C["pushedAt"]: "2026-01-01T00:00:00Z",
    }
    linha.update(overrides)
    return linha


def test_calcular_rq06_exclui_repos_com_total_zero():
    df = pd.DataFrame([
        _linha(**{C["closedIssues"]: 0, ISSUES_ABERTAS_COL: 0}),  # total=0, excluído
        _linha(**{C["closedIssues"]: 5, ISSUES_ABERTAS_COL: 5}),  # ratio=0.5
        _linha(**{C["closedIssues"]: 10, ISSUES_ABERTAS_COL: 0}),  # ratio=1.0
    ])

    rq06 = calcular_rq06(df)

    assert rq06["n_considerados"] == 2
    assert rq06["n_excluidos_zero_issues"] == 1
    assert rq06["median"] == 0.75
    assert rq06["min"] == 0.5
    assert rq06["max"] == 1.0


def test_calcular_rq07_agrupa_sem_linguagem_e_ordena_por_n():
    agora = pd.Timestamp("2026-01-10T00:00:00Z")
    df = pd.DataFrame([
        _linha(**{C["primaryLanguage"]: None, C["mergedPRs"]: 4, C["pushedAt"]: "2026-01-01T00:00:00Z"}),
        _linha(**{C["primaryLanguage"]: None, C["mergedPRs"]: 6, C["pushedAt"]: "2026-01-05T00:00:00Z"}),
        _linha(**{C["primaryLanguage"]: "Go", C["mergedPRs"]: 20, C["pushedAt"]: "2026-01-08T00:00:00Z"}),
    ])

    rq07 = calcular_rq07(df, agora=agora)
    por_linguagem = {r["linguagem"]: r for r in rq07}

    assert rq07[0]["linguagem"] == SEM_LINGUAGEM
    assert por_linguagem[SEM_LINGUAGEM]["n"] == 2
    assert por_linguagem[SEM_LINGUAGEM]["mediana_prs"] == 5.0
    assert por_linguagem["Go"]["n"] == 1
    assert por_linguagem["Go"]["mediana_dias_push"] == 2.0


def test_calcular_rq07_teste_hipotese_separa_populares_por_top_n_e_ignora_sem_linguagem():
    df = pd.DataFrame([
        _linha(**{C["primaryLanguage"]: "A", C["mergedPRs"]: 100}),
        _linha(**{C["primaryLanguage"]: "A", C["mergedPRs"]: 110}),
        _linha(**{C["primaryLanguage"]: "A", C["mergedPRs"]: 120}),
        _linha(**{C["primaryLanguage"]: "B", C["mergedPRs"]: 90}),
        _linha(**{C["primaryLanguage"]: "B", C["mergedPRs"]: 95}),
        _linha(**{C["primaryLanguage"]: "C", C["mergedPRs"]: 1}),
        _linha(**{C["primaryLanguage"]: "D", C["mergedPRs"]: 2}),
        _linha(**{C["primaryLanguage"]: None, C["mergedPRs"]: 9999}),  # sem linguagem: ignorado
    ])

    teste = calcular_rq07_teste_hipotese(df, top_n=2)

    assert teste["linguagens_populares"] == ["A", "B"]
    metrica = teste["metricas"]["mergedPRs"]
    assert metrica["n_populares"] == 5
    assert metrica["n_demais"] == 2
    assert metrica["mediana_populares"] == 100.0
    assert metrica["mediana_demais"] == 1.5
    assert 0.0 <= metrica["p_value"] <= 1.0
