"""CFR (c) por issues e classificação do repositório (Issue #45)."""
import math
from datetime import date

import pandas as pd
import pytest

from metricas.classificacao import classificar_repo
from metricas.cfr import cfr_issues

FIM = date(2025, 9, 30)


def _rels(*publicadas, na_janela=True):
    return pd.DataFrame({
        "repo": "o/r", "tag": [f"v{i}" for i in range(len(publicadas))],
        "publicada_em": list(publicadas), "prerelease": False,
        "na_janela": na_janela, "body": "",
    })


def _issues(*criadas, cita=True):
    return pd.DataFrame({
        "repo": "o/r", "numero": range(1, len(criadas) + 1),
        "criada_em": list(criadas), "labels": "bug", "titulo": "x",
        "cita_tag": cita,
    })


R = "2025-03-10T12:00:00Z"


@pytest.mark.parametrize("criada, falhou", [
    ("2025-03-10T11:59:59Z", False),   # antes da release
    ("2025-03-10T12:00:00Z", True),    # dia 0
    ("2025-03-17T12:00:00Z", True),    # exatamente n_dias
    ("2025-03-17T12:00:01Z", False),   # um segundo depois
    ("2025-03-18T12:00:00Z", False),   # n_dias + 1
])
def test_bordas_da_janela_de_n_dias(criada, falhou):
    assert cfr_issues(_rels(R), _issues(criada), 7, "janela", FIM) == (1.0 if falhou else 0.0)


def test_proporcao_de_releases_que_falharam():
    rels = _rels("2025-01-01T00:00:00Z", "2025-02-01T00:00:00Z",
                 "2025-03-01T00:00:00Z", "2025-04-01T00:00:00Z")
    iss = _issues("2025-01-03T00:00:00Z", "2025-03-02T00:00:00Z")
    assert cfr_issues(rels, iss, 7, "janela", FIM) == 0.5


def test_varias_issues_na_mesma_release_contam_uma_falha():
    iss = _issues("2025-03-11T00:00:00Z", "2025-03-12T00:00:00Z", "2025-03-13T00:00:00Z")
    rels = _rels(R, "2025-06-01T00:00:00Z")
    assert cfr_issues(rels, iss, 7, "janela", FIM) == 0.5


def test_modo_citacao_exige_a_tag_no_texto():
    rels = _rels(R)
    sem_citar = _issues("2025-03-11T00:00:00Z", cita=False)
    assert cfr_issues(rels, sem_citar, 7, "janela", FIM) == 1.0
    assert cfr_issues(rels, sem_citar, 7, "citacao", FIM) == 0.0
    citando = _issues("2025-03-11T00:00:00Z", cita=True)
    assert cfr_issues(rels, citando, 7, "citacao", FIM) == 1.0


def test_censura_nos_ultimos_n_dias_da_janela():
    # Release 3 dias antes do fim: com n_dias=7 não dá tempo de observar.
    censurada = "2025-09-27T00:00:00Z"
    ok = "2025-03-01T00:00:00Z"
    rels = _rels(ok, censurada)
    iss = _issues("2025-09-28T00:00:00Z")      # issue que "pegaria" a censurada
    # A censurada sai do denominador; a release ok não teve issue: 0/1.
    assert cfr_issues(rels, iss, 7, "janela", FIM) == 0.0


def test_censura_no_limite_exato():
    # publicada_em + 7 dias == fim da janela (23:59:59): ainda observável.
    limite = "2025-09-23T23:59:59Z"
    iss = _issues("2025-09-24T00:00:00Z")
    assert cfr_issues(_rels(limite), iss, 7, "janela", FIM) == 1.0
    # Um segundo depois já passa do fim.
    assert math.isnan(cfr_issues(_rels("2025-09-24T00:00:00Z"), iss, 7, "janela", FIM))


def test_so_censuradas_e_nan():
    assert math.isnan(cfr_issues(_rels("2025-09-29T00:00:00Z"), _issues("2025-09-30T00:00:00Z"),
                                 7, "janela", FIM))


def test_repo_sem_issues_de_bug_e_nan_e_nao_zero():
    vazio = _issues()
    assert math.isnan(cfr_issues(_rels(R), vazio, 7, "janela", FIM))


def test_release_fora_da_janela_nao_entra():
    rels = _rels(R, na_janela=False)
    assert math.isnan(cfr_issues(rels, _issues("2025-03-11T00:00:00Z"), 7, "janela", FIM))


def test_sem_releases_e_nan():
    assert math.isnan(cfr_issues(_rels(), _issues("2025-03-11T00:00:00Z"), 7, "janela", FIM))


def test_modo_invalido():
    with pytest.raises(ValueError, match="modo"):
        cfr_issues(_rels(R), _issues(R), 7, "outro", FIM)


# --- classificar_repo -------------------------------------------------------

@pytest.mark.parametrize("notas, classe, nota", [
    ((4, 3, 3, 1), "High", 3),
    ((3, 3, 2, 2), "Medium", 2),      # 2,5 arredonda para baixo
    ((4, 4, 4, 4), "Elite", 4),
    ((1, 1, 1, 1), "Low", 1),
    ((4, 4, 1, 1), "Medium", 2),      # 2,5
    ((4, 3, 2, 1), "Medium", 2),      # 2,5
    ((4, 4, 3, 1), "High", 3),
    ((2, 3, math.nan, 3), "High", 3),   # NaN sai da conta
    ((4, math.nan, math.nan, math.nan), "Elite", 4),
    ((3, 2), "Medium", 2),
])
def test_classe_pela_mediana_para_baixo(notas, classe, nota):
    assert classificar_repo(notas) == (classe, nota)


def test_todas_nan_nao_tem_classe():
    classe, nota = classificar_repo([math.nan] * 4)
    assert classe is None and math.isnan(nota)


def test_sem_notas_nao_tem_classe():
    assert classificar_repo([])[0] is None


def test_nota_fora_do_intervalo():
    with pytest.raises(ValueError):
        classificar_repo([5, 3])
    with pytest.raises(ValueError):
        classificar_repo([2.5, 3])


def test_resultado_respeita_o_contrato_de_classe_e_nota():
    from metricas.schemas import NOTAS_DORA
    classe, nota = classificar_repo((4, 3, 3, 1))
    assert NOTAS_DORA[classe] == nota


# --- classificar_metrica: todos os cortes exatos da tabela -------------------

from metricas.classificacao import classificar_metrica  # noqa: E402


@pytest.mark.parametrize("valor, nota", [
    (14, 4), (7.0, 4), (6.99, 3), (1.0, 3), (0.99, 2),
    (1 / 4.34, 2), (0.23, 1), (0.0, 1),
])
def test_cortes_de_frequencia(valor, nota):
    assert classificar_metrica("freq", valor) == nota


@pytest.mark.parametrize("horas, nota", [
    (0, 4), (23.99, 4), (24.0, 3), (167.99, 3), (168.0, 2),
    (719.99, 2), (720.0, 1), (5000, 1),
])
def test_cortes_de_lead_time(horas, nota):
    assert classificar_metrica("lead_time", horas) == nota


@pytest.mark.parametrize("proporcao, nota", [
    (0.0, 4), (0.15, 4), (0.1501, 3), (0.30, 3), (0.3001, 2),
    (0.45, 2), (0.4501, 1), (1.0, 1),
])
def test_cortes_de_cfr(proporcao, nota):
    assert classificar_metrica("cfr", proporcao) == nota


@pytest.mark.parametrize("horas, nota", [
    (0.0, 4), (0.99, 4), (1.0, 3), (23.99, 3), (24.0, 2),
    (167.99, 2), (168.0, 1), (1000, 1),
])
def test_cortes_de_recuperacao(horas, nota):
    assert classificar_metrica("recuperacao", horas) == nota


@pytest.mark.parametrize("nome", ["freq", "lead_time", "cfr", "recuperacao"])
def test_valor_nan_da_nota_nan(nome):
    assert math.isnan(classificar_metrica(nome, math.nan))


def test_metrica_desconhecida():
    with pytest.raises(ValueError, match="desconhecida"):
        classificar_metrica("mttr", 1.0)
