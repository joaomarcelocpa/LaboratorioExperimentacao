"""Motor de simulação Monte Carlo: t de Welch × Mann-Whitney.

Gera dois grupos lognormais, aplica os dois testes bicaudais e devolve a
proporção de p < alfa de cada um. Com efeito zero essa proporção é o erro
tipo I (Q1); com efeito > 0 é o poder (Q2 e Q3).

Parâmetros de referência: média dos parâmetros dos dois grupos reais
(src/gerador.PARAMS), de modo que sob H0 os dois grupos têm a mesma
distribuição.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.gerador import PARAMS
from src.testes import ALFA

REPETICOES = 10_000
SEMENTE = 42

N_REAL = PARAMS["com_bot"]["n"]
MU_REF = (PARAMS["com_bot"]["mu"] + PARAMS["sem_bot"]["mu"]) / 2
SIGMA_REF = (PARAMS["com_bot"]["sigma"] + PARAMS["sem_bot"]["sigma"]) / 2

SAIDA = Path(__file__).parent.parent / "data" / "simulated"


def simular(
    n: int = N_REAL,
    razao_medianas: float = 1.0,
    sigma: float = SIGMA_REF,
    repeticoes: int = REPETICOES,
    seed: int = SEMENTE,
    alfa: float = ALFA,
) -> dict[str, float]:
    """Proporção de rejeições de H0 de cada teste.

    n: observações por grupo.
    razao_medianas: mediana do grupo B dividida pela do grupo A. 1 = sem efeito
        (H0 verdadeira). Implementado deslocando o μ do log do grupo B por ln(razão).
    sigma: σ do log nos dois grupos, que controla a assimetria (maior = mais cauda).
    """
    if razao_medianas <= 0:
        raise ValueError("razao_medianas deve ser positiva")
    rng = np.random.default_rng(seed)
    a = rng.lognormal(MU_REF, sigma, size=(repeticoes, n))
    b = rng.lognormal(MU_REF + np.log(razao_medianas), sigma, size=(repeticoes, n))

    p_welch = stats.ttest_ind(a, b, axis=1, equal_var=False).pvalue
    p_mw = stats.mannwhitneyu(a, b, axis=1, alternative="two-sided").pvalue
    return {
        "welch": float((p_welch < alfa).mean()),
        "mann_whitney": float((p_mw < alfa).mean()),
    }


def margem_de_erro(proporcao: float, repeticoes: int = REPETICOES) -> float:
    """Margem de erro de 95% da proporção estimada (aproximação normal)."""
    return 1.96 * np.sqrt(proporcao * (1 - proporcao) / repeticoes)


def q1(
    n: int = N_REAL, sigma: float = SIGMA_REF, repeticoes: int = REPETICOES, seed: int = SEMENTE
) -> pd.DataFrame:
    """Q1: erro tipo I de cada teste, com H0 verdadeira (razão de medianas = 1)."""
    taxas = simular(n=n, razao_medianas=1.0, sigma=sigma, repeticoes=repeticoes, seed=seed)
    return pd.DataFrame(
        [
            {
                "teste": teste,
                "n": n,
                "sigma_log": sigma,
                "repeticoes": repeticoes,
                "erro_tipo_i": taxa,
                "margem_erro_95": margem_de_erro(taxa, repeticoes),
            }
            for teste, taxa in taxas.items()
        ]
    )


if __name__ == "__main__":
    resultado = q1()
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "q1_erro_tipo_i.csv"
    resultado.to_csv(destino, index=False)
    print(resultado.round(4).to_string(index=False))
    print(f"\nSalvo em {destino}")
