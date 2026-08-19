"""Testes do validador de integridade das colunas de RQ06/RQ07."""
import pandas as pd
import pytest

from validate_rq06_rq07_integrity import COLS, gerar_relatorio

C = COLS


def _linha_valida(**overrides):
    """Monta uma linha base válida (colunas reais de repositorios.csv), sobrescrevendo campos pontuais."""
    linha = {
        C["autor"]: "octocat",
        C["nome_repositorio"]: "hello-world",
        C["issues_abertas"]: 10,
        C["issues_fechadas"]: 10,
        C["prs_mergeadas"]: 5,
        C["releases"]: 3,
        C["atualizado_em"]: "2026-01-01T00:00:00Z",
        C["linguagem"]: "Python",
    }
    linha.update(overrides)
    return linha


def test_nulo_em_coluna_obrigatoria_falha():
    df = pd.DataFrame([
        _linha_valida(),
        _linha_valida(**{C["issues_fechadas"]: None, C["nome_repositorio"]: "other"}),
    ])

    relatorio = gerar_relatorio(df)

    assert relatorio["status"] == "FALHA"
    assert relatorio["schema_ok"] is False


def test_issues_fechadas_maior_que_total_de_issues_falha():
    """issues_abertas negativo faz total (abertas+fechadas) cair abaixo de fechadas."""
    df = pd.DataFrame([
        _linha_valida(),
        _linha_valida(**{
            C["nome_repositorio"]: "other",
            C["issues_abertas"]: -5,
            C["issues_fechadas"]: 10,
        }),
    ])

    relatorio = gerar_relatorio(df)

    assert relatorio["status"] == "FALHA"
    assert relatorio["schema_ok"] is False


def test_atualizado_em_no_futuro_falha():
    agora = pd.Timestamp("2026-01-01T00:00:00Z")
    df = pd.DataFrame([
        _linha_valida(**{C["atualizado_em"]: "2026-06-01T00:00:00Z"}),
    ])

    relatorio = gerar_relatorio(df, agora=agora)

    assert relatorio["status"] == "FALHA"
    assert len(relatorio["pushed_at_futuro"]) == 1
