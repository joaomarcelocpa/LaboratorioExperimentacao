"""Gera o dashboard do Lab 04 (dashboard.html), no mesmo formato dos Labs 1 e 2.

A página é um único HTML com os dados embutidos: abre com duplo clique, sem servidor.
Os dados vêm de data/raw/prs.csv e data/simulated/*.csv; a grade do gráfico
interativo de poder é calculada aqui com o motor de src/simulacao.py.

Uso:
    python -m src.painel           # gera dashboard.html
    python -m src.painel --abrir   # gera e abre no navegador
"""

import json
import sys
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.gerador import PARAMS, gerar_dados
from src.q3 import SITUACOES
from src.simulacao import N_REAL, REPETICOES, SEMENTE, SIGMA_REF, simular
from src.testes import ALFA, aplicar_testes

RAIZ = Path(__file__).parent.parent
TEMPLATE = Path(__file__).parent / "painel_template.html"
DESTINO = RAIZ / "dashboard.html"

LINK_REPOSITORIO = "https://github.com/joaomarcelocpa/LaboratorioExperimentacao"
LINK_PROJECTS = "https://github.com/users/joaomarcelocpa/projects/2"

# Grade do gráfico interativo: cada combinação é simulada uma vez (2.000 repetições).
GRADE_N = [10, 20, 30, 50, 100, 200]
GRADE_SIGMA = [1.0, 1.5, 2.0, round(float(SIGMA_REF), 2), 3.0, 3.5]
GRADE_RAZOES = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
GRADE_REPETICOES = 2_000

ALFA_MENOR = 0.01  # pergunta 12: o que mudaria com α = 0,01


def _g2(t_obs: float, gl: float) -> dict:
    """Curva da estatística t sob H0, região de rejeição e p-valor do exemplo do G2."""
    dist = stats.t(gl)
    x = np.linspace(-4.5, 4.5, 181)
    return {
        "t_obs": float(t_obs),
        "gl": float(gl),
        "p": float(2 * dist.sf(abs(t_obs))),
        "t_crit": float(dist.ppf(1 - ALFA / 2)),
        "x": [round(float(v), 3) for v in x],
        "y": [round(float(v), 5) for v in dist.pdf(x)],
    }


def _reais() -> dict:
    dados = pd.read_csv(RAIZ / "data" / "raw" / "prs.csv")
    grupos = {g: dados[dados["grupo"] == g]["horas_ate_merge"].to_numpy() for g in PARAMS}
    com_bot, sem_bot = grupos["com_bot"], grupos["sem_bot"]
    r = aplicar_testes(com_bot, sem_bot)
    return {
        "horas": {g: [float(v) for v in vals] for g, vals in grupos.items()},
        "n": {g: int(len(vals)) for g, vals in grupos.items()},
        "mediana": {g: float(np.median(v)) for g, v in grupos.items()},
        "media": {g: float(np.mean(v)) for g, v in grupos.items()},
        "maximo": {g: float(np.max(v)) for g, v in grupos.items()},
        "welch": {k: float(v) for k, v in r["welch"].items()},
        "mann_whitney": {k: float(v) for k, v in r["mann_whitney"].items()},
        "d_cohen": float(r["d_cohen"]),
        "d_cohen_log": float(r["d_cohen_log"]),
        "prob_superioridade": float(r["prob_superioridade"]),
        "concordam": r["concordam"],
    }


def _grade_poder() -> dict:
    """Poder dos dois testes para cada (n, sigma, razão): valores[i_n][i_sigma][i_razao] = [welch, mw]."""
    valores = []
    for n in GRADE_N:
        por_sigma = []
        for sigma in GRADE_SIGMA:
            por_razao = []
            for razao in GRADE_RAZOES:
                t = simular(n=n, razao_medianas=razao, sigma=sigma, repeticoes=GRADE_REPETICOES)
                por_razao.append([round(t["welch"], 4), round(t["mann_whitney"], 4)])
            por_sigma.append(por_razao)
        valores.append(por_sigma)
    return {
        "n": GRADE_N,
        "sigma": GRADE_SIGMA,
        "razoes": GRADE_RAZOES,
        "repeticoes": GRADE_REPETICOES,
        "valores": valores,
    }


def _alfa_menor() -> list[dict]:
    """P12: o que muda com α = 0,01. Erro tipo I (razão 1) e poder (razões 2 e 5) por situação."""
    situacoes = {"base": {"n": N_REAL, "sigma": SIGMA_REF}, **SITUACOES}
    linhas = []
    for nome, params in situacoes.items():
        for razao in (1.0, 2.0, 5.0):
            taxas = simular(razao_medianas=razao, alfa=ALFA_MENOR, **params)
            for teste, taxa in taxas.items():
                linhas.append(
                    {"situacao": nome, "razao_medianas": razao, "teste": teste, "taxa": round(taxa, 4)}
                )
    return linhas


def montar_dados() -> dict:
    simulados = gerar_dados(seed=SEMENTE)
    reais = _reais()
    r_sim = aplicar_testes(simulados["com_bot"], simulados["sem_bot"])
    pasta = RAIZ / "data" / "simulated"
    return {
        "links": {"repositorio": LINK_REPOSITORIO, "projects": LINK_PROJECTS},
        "config": {"alfa": ALFA, "repeticoes": REPETICOES, "semente": SEMENTE},
        "params": PARAMS,
        "sigma_ref": float(SIGMA_REF),
        "reais": reais,
        "simulados": {g: [float(v) for v in vals] for g, vals in simulados.items()},
        "g2": _g2(r_sim["welch"]["t"], r_sim["welch"]["gl"]),
        "q1": pd.read_csv(pasta / "q1_erro_tipo_i.csv").to_dict("records"),
        "q2": pd.read_csv(pasta / "q2_poder.csv").to_dict("records"),
        "q3": pd.read_csv(pasta / "q3_situacoes.csv").to_dict("records"),
        "alfa_menor": {"alfa": ALFA_MENOR, "linhas": _alfa_menor()},
        "grade": _grade_poder(),
    }


def gerar(destino: Path = DESTINO) -> Path:
    """Escreve o dashboard.html com os dados embutidos."""
    dados = json.dumps(montar_dados(), ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DADOS__", dados)
    destino.write_text(html, encoding="utf-8")
    return destino


if __name__ == "__main__":
    caminho = gerar()
    print(f"Dashboard salvo em {caminho}")
    if "--abrir" in sys.argv:
        webbrowser.open(caminho.as_uri())
