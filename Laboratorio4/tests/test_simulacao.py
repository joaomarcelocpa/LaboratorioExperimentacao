import numpy as np
from scipy import stats

from src.simulacao import MU_REF, SIGMA_REF, margem_de_erro, q1, simular


def test_mesma_semente_mesmo_resultado():
    assert simular(repeticoes=500, seed=1) == simular(repeticoes=500, seed=1)


def test_vetorizado_igual_ao_calculo_repeticao_a_repeticao():
    reps, n = 200, 30
    rng = np.random.default_rng(7)
    a = rng.lognormal(MU_REF, SIGMA_REF, size=(reps, n))
    b = rng.lognormal(MU_REF + np.log(2.0), SIGMA_REF, size=(reps, n))
    welch = [stats.ttest_ind(x, y, equal_var=False).pvalue < 0.05 for x, y in zip(a, b)]
    mw = [
        stats.mannwhitneyu(x, y, alternative="two-sided").pvalue < 0.05
        for x, y in zip(a, b)
    ]
    esperado = {"welch": float(np.mean(welch)), "mann_whitney": float(np.mean(mw))}
    assert simular(razao_medianas=2.0, repeticoes=reps, seed=7) == esperado


def test_poder_cresce_com_o_efeito():
    fraco = simular(razao_medianas=1.5, repeticoes=2000)
    forte = simular(razao_medianas=5.0, repeticoes=2000)
    assert forte["mann_whitney"] > fraco["mann_whitney"]
    assert forte["welch"] > fraco["welch"]


def test_q1_mann_whitney_perto_de_5_por_cento():
    linha = q1().set_index("teste").loc["mann_whitney"]
    assert abs(linha.erro_tipo_i - 0.05) < 0.01


def test_margem_de_erro_de_10000_repeticoes():
    assert abs(margem_de_erro(0.05, 10_000) - 0.0043) < 0.0002
