"""Testes do validador de integridade das colunas de RQ06/RQ07."""
import pandas as pd
import pytest

from validate_rq06_rq07_integrity import COLS, gerar_relatorio

C = COLS


def _linha_valida(**overrides):
    """Monta uma linha base válida, sobrescrevendo campos pontuais."""
    linha = {
        C["name_with_owner"]: "octocat/hello-world",
        C["closed_issues"]: 10,
        C["total_issues"]: 20,
        C["merged_prs"]: 5,
        C["releases_count"]: 3,
        C["pushed_at"]: "2026-01-01T00:00:00Z",
        C["primary_language"]: "Python",
    }
    linha.update(overrides)
    return linha


def test_nulo_em_coluna_obrigatoria_falha():
    df = pd.DataFrame([
        _linha_valida(),
        _linha_valida(**{C["closed_issues"]: None, C["name_with_owner"]: "octocat/other"}),
    ])

    relatorio = gerar_relatorio(df)

    assert relatorio["status"] == "FALHA"
    assert relatorio["schema_ok"] is False


def test_closed_issues_maior_que_total_issues_falha():
    df = pd.DataFrame([
        _linha_valida(),
        _linha_valida(**{
            C["name_with_owner"]: "octocat/other",
            C["closed_issues"]: 30,
            C["total_issues"]: 20,
        }),
    ])

    relatorio = gerar_relatorio(df)

    assert relatorio["status"] == "FALHA"
    assert relatorio["schema_ok"] is False


def test_pushed_at_no_futuro_falha():
    agora = pd.Timestamp("2026-01-01T00:00:00Z")
    df = pd.DataFrame([
        _linha_valida(**{C["pushed_at"]: "2026-06-01T00:00:00Z"}),
    ])

    relatorio = gerar_relatorio(df, agora=agora)

    assert relatorio["status"] == "FALHA"
    assert len(relatorio["pushed_at_futuro"]) == 1
