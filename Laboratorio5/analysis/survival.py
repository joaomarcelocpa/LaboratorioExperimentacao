"""Kaplan-Meier e teste log-rank para o passo da primeira regressão.

Evento: primeira ocorrência de reg_failed > 0 num passo >= 1. Cadeia sem
regressão até o fim, ou que terminou por falha de execução, é censurada no
último passo concluído com sucesso (PLANEJAMENTO.pdf, 3.2 e 3.6).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


TRATAMENTOS_DA_FALHA = ("censura", "evento", "exclui")


def tempos_ate_regressao(df: pd.DataFrame, falha: str = "censura") -> pd.DataFrame:
    """Uma linha por (chain_id, mode): tempo (passo) e evento (1 = regrediu).

    `falha` diz o que fazer com a cadeia que terminou por passo falho antes de
    regredir (análise de sensibilidade da #125):
      censura  censurada no último passo ok (tratamento principal, PDF 3.6);
      evento   o passo falho conta como a primeira regressão (pior caso);
      exclui   a cadeia sai da análise.
    """
    if falha not in TRATAMENTOS_DA_FALHA:
        raise ValueError(f"falha deve ser um de {TRATAMENTOS_DA_FALHA}")
    linhas = []
    for (cadeia, modo), g in df.groupby(["chain_id", "mode"]):
        g = g[g["step"] >= 1].sort_values("step")
        ok = g[g["status"] == "ok"]
        reg = ok[ok["reg_failed"] > 0]
        falhou = (g["status"] == "falha").any()
        if len(reg):
            linhas.append((cadeia, modo, int(reg["step"].iloc[0]), 1, int(falhou)))
        elif falhou and falha == "evento":
            linhas.append((cadeia, modo, int(g[g["status"] == "falha"]["step"].min()), 1, 1))
        elif falhou and falha == "exclui":
            continue
        else:
            ultimo = int(ok["step"].max()) if len(ok) else 0
            linhas.append((cadeia, modo, ultimo, 0, int(falhou)))
    return pd.DataFrame(linhas, columns=["chain_id", "mode", "tempo", "evento", "terminou_por_falha"])


def kaplan_meier(tempo, evento) -> pd.DataFrame:
    """Estimador de Kaplan-Meier com IC 95% de Greenwood (escala log-log)."""
    tempo = np.asarray(tempo, dtype=int)
    evento = np.asarray(evento, dtype=int)
    instantes = np.unique(tempo[evento == 1])
    s = 1.0
    soma_gw = 0.0
    linhas = [(0, len(tempo), 0, 1.0, 1.0, 1.0)]
    for t in instantes:
        n_risco = int((tempo >= t).sum())
        d = int(((tempo == t) & (evento == 1)).sum())
        s *= 1 - d / n_risco
        if n_risco > d:
            soma_gw += d / (n_risco * (n_risco - d))
        if 0 < s < 1 and soma_gw > 0:
            erro = np.sqrt(soma_gw) / abs(np.log(s))
            inf, sup = s ** np.exp(1.96 * erro), s ** np.exp(-1.96 * erro)
        else:
            inf = sup = s
        linhas.append((int(t), n_risco, d, s, inf, sup))
    return pd.DataFrame(linhas, columns=["tempo", "em_risco", "eventos", "sobrevivencia", "ic_inf", "ic_sup"])


def log_rank(tempo, evento, grupo) -> tuple[float, float]:
    """Log-rank de dois grupos. Devolve (qui-quadrado, p com 1 grau de liberdade).

    Se não há nenhum evento, não há o que comparar: devolve (0.0, 1.0).
    """
    tempo = np.asarray(tempo, dtype=int)
    evento = np.asarray(evento, dtype=int)
    grupo = np.asarray(grupo)
    primeiro = np.unique(grupo)[0]
    em_a = grupo == primeiro
    o_menos_e = 0.0
    var = 0.0
    for t in np.unique(tempo[evento == 1]):
        n = int((tempo >= t).sum())
        n_a = int(((tempo >= t) & em_a).sum())
        d = int(((tempo == t) & (evento == 1)).sum())
        d_a = int(((tempo == t) & (evento == 1) & em_a).sum())
        o_menos_e += d_a - d * n_a / n
        if n > 1:
            var += d * (n_a / n) * (1 - n_a / n) * (n - d) / (n - 1)
    if var <= 0:
        return 0.0, 1.0
    qui = o_menos_e**2 / var
    return float(qui), float(stats.chi2.sf(qui, 1))
