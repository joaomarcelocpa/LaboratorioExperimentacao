import numpy as np

from src.gerador import gerar_dados
from src.testes import aplicar_testes


def test_testes_sobre_conjunto_simulado_com_semente_fixa():
    dados = gerar_dados(seed=42)
    r = aplicar_testes(dados["com_bot"], dados["sem_bot"])
    assert 0 <= r["welch"]["p"] <= 1
    assert 0 <= r["mann_whitney"]["p"] <= 1
    assert r["mann_whitney"]["p"] < 0.05 < r["welch"]["p"]
    assert r["concordam"] is False


def test_prob_superioridade_entre_zero_e_um():
    dados = gerar_dados(seed=1)
    r = aplicar_testes(dados["com_bot"], dados["sem_bot"])
    assert 0 <= r["prob_superioridade"] <= 1
    assert np.isclose(r["prob_superioridade"], r["mann_whitney"]["U"] / 900)
