"""Q2: poder dos dois testes para tamanhos de efeito crescentes.

Chama simular() com pelo menos 5 razões de medianas (começando em 1 = H0 verdadeira)
e salva a proporção de rejeições de cada teste em data/simulated/q2_poder.csv.
"""

from pathlib import Path

import pandas as pd

from src.simulacao import SIGMA_REF, simular

RAZOES = [1.0, 1.5, 2.0, 3.0, 5.0]

SAIDA = Path(__file__).parent.parent / "data" / "simulated" / "q2_poder.csv"


def calcular_poder(razoes: list[float] = RAZOES) -> pd.DataFrame:
    """Roda simular() para cada razão de medianas e devolve DataFrame longo."""
    linhas = []
    for razao in razoes:
        taxas = simular(razao_medianas=razao)
        for teste, poder in taxas.items():
            linhas.append({"razao_medianas": razao, "teste": teste, "poder": poder})
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    df = calcular_poder()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False)
    print(df.to_string(index=False))
    print(f"\nSalvo em {SAIDA}")
