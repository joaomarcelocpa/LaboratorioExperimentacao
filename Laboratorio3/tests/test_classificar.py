"""Tabela de conclusion da seção 3 do enunciado."""
import logging

import pytest

from coleta.runs import classificar, desconhecidas, esquecer_desconhecidas


@pytest.fixture(autouse=True)
def limpar():
    esquecer_desconhecidas()
    yield
    esquecer_desconhecidas()


@pytest.mark.parametrize("conclusion", ["success"])
def test_sucesso(conclusion):
    assert classificar(conclusion) == "sucesso"


@pytest.mark.parametrize("conclusion", ["failure", "timed_out", "startup_failure"])
def test_falha(conclusion):
    assert classificar(conclusion) == "falha"


@pytest.mark.parametrize("conclusion", [
    "cancelled", "skipped", "neutral", "action_required", "stale",
])
def test_ignorado(conclusion):
    assert classificar(conclusion) == "ignorado"


@pytest.mark.parametrize("conclusion", [None, "", "   "])
def test_execucao_em_andamento_e_ignorada(conclusion):
    # conclusion vazio = run ainda rodando. Não entra em nenhum cálculo.
    assert classificar(conclusion) == "ignorado"


def test_maiusculas_nao_importam():
    assert classificar("SUCCESS") == "sucesso"
    assert classificar("Failure") == "falha"


def test_valor_desconhecido_vira_ignorado():
    # Um conclusion que o GitHub venha a inventar não pode inflar o CFR
    # sozinho: o default conservador é ignorar.
    assert classificar("explodiu") == "ignorado"


def test_valor_desconhecido_e_contado():
    classificar("explodiu")
    classificar("explodiu")
    classificar("outro_novo")

    assert desconhecidas() == {"explodiu": 2, "outro_novo": 1}


def test_valor_conhecido_nao_e_contado():
    classificar("success")
    classificar("cancelled")
    classificar(None)

    assert desconhecidas() == {}


def test_valor_novo_e_logado_uma_vez_so(caplog):
    with caplog.at_level(logging.WARNING, logger="coleta.runs"):
        classificar("explodiu")
        classificar("explodiu")
        classificar("explodiu")

    avisos = [r for r in caplog.records if "explodiu" in r.getMessage()]
    assert len(avisos) == 1, "o aviso deve sair no primeiro valor novo, não em todo run"


def test_esquecer_zera_o_contador():
    classificar("explodiu")
    esquecer_desconhecidas()

    assert desconhecidas() == {}
