"""Q3: erro tipo I e poder dos dois testes em situações que violam os pressupostos do t de Welch.

Repete Q1 (razão de medianas = 1) e Q2 (demais razões) em cada situação ruim e salva
em data/simulated/q3_situacoes.csv, com as colunas situacao, razao_medianas, teste e taxa.
Com razao_medianas = 1 a taxa é o erro tipo I; com razao_medianas > 1 é o poder.
"""

from pathlib import Path

import pandas as pd

from src.q2 import RAZOES
from src.simulacao import N_REAL, SIGMA_REF, simular

SITUACOES = {
    "cauda_mais_longa": {"n": N_REAL, "sigma": 3.5},
    "amostra_pequena": {"n": 10, "sigma": SIGMA_REF},
    "pequena_e_cauda_longa": {"n": 10, "sigma": 3.5},
}

SAIDA = Path(__file__).parent.parent / "data" / "simulated" / "q3_situacoes.csv"


def calcular_q3(situacoes: dict = SITUACOES, razoes: list[float] = RAZOES) -> pd.DataFrame:
    """Roda simular() para cada situação e razão de medianas; devolve DataFrame longo."""
    linhas = []
    for nome, params in situacoes.items():
        for razao in razoes:
            taxas = simular(razao_medianas=razao, **params)
            for teste, taxa in taxas.items():
                linhas.append(
                    {"situacao": nome, "razao_medianas": razao, "teste": teste, "taxa": taxa}
                )
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    df = calcular_q3()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False)
    print(df.pivot_table(index=["situacao", "razao_medianas"], columns="teste", values="taxa")
          .round(4).to_string())
    print(f"\nSalvo em {SAIDA}")
