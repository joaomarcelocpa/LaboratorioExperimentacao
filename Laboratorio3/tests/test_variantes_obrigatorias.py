"""Toda variante exigida pelo enunciado tem coluna em metricas.csv (Issue #66).

Cada linha cita a RQ do ESPECIFICACAO.md que exige a variante. Se o contrato
perder uma dessas colunas, a análise das RQs deixa de ser possível.
"""
import pytest

from metricas.schemas import SCHEMAS

OBRIGATORIAS = {
    "RQ01 release": "freq_release",
    "RQ01/RQ07 release + pré-release": "freq_release_pre",
    "RQ07 tag": "freq_tag",
    "RQ07 deployment em produção": "freq_deploy",
    "RQ02 lead time (a), por release": "lt_release_h",
    "RQ02 lead time (b), por commit": "lt_commit_h",
    "RQ02 lead time (b) sem bots": "lt_commit_sem_bots_h",
    "RQ03 CFR (a), CI oficial": "cfr_a",
    "RQ03 CFR (a) bruto, com tentativas": "cfr_a_bruto",
    "RQ03 CFR (a) sem flaky": "cfr_a_sem_flaky",
    "RQ03 CFR (b), release corretiva": "cfr_b",
    "RQ03 CFR (c), issue de bug": "cfr_c",
    "RQ04 tempo de recuperação": "recuperacao_h",
    "RQ04 recuperação sem episódios só de flaky": "recuperacao_sem_flaky_h",
    "RQ04 proporção de censurados": "pct_censurados",
    "RQ04 recuperação por release": "recuperacao_releases_h",
    "RQ07/classificação DORA": "classe_dora",
    "RQ07 nota para o kappa ponderado": "classe_dora_nota",
    "RQ08a rework rate": "rework_rate",
    "RQ08a rework rate em 7 dias": "rework_rate_7d",
}


@pytest.mark.parametrize("variante, coluna", OBRIGATORIAS.items())
def test_variante_tem_coluna_em_metricas_csv(variante, coluna):
    assert coluna in SCHEMAS["metricas"].colunas, variante


def test_serie_mensal_da_rq08b_existe():
    assert {"cfr_a", "recuperacao_h", "runs_validos"} <= set(
        SCHEMAS["metricas_mensais"].colunas)
