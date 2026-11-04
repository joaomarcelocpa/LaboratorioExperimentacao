"""Aplica t de Welch e Mann-Whitney a um conjunto simulado."""

import numpy as np
from scipy import stats

from src.gerador import gerar_dados

ALFA = 0.05


def cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """d de Cohen com desvio-padrão combinado."""
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (a.mean() - b.mean()) / sp


def prob_superioridade(a: np.ndarray, b: np.ndarray) -> float:
    """P(A > B) + 0,5 P(A = B): tamanho de efeito natural do Mann-Whitney."""
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return u / (len(a) * len(b))


def aplicar_testes(a: np.ndarray, b: np.ndarray) -> dict:
    """Roda os dois testes bicaudais e devolve estatísticas e tamanhos de efeito."""
    welch = stats.ttest_ind(a, b, equal_var=False)
    mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "welch": {"t": welch.statistic, "gl": welch.df, "p": welch.pvalue},
        "mann_whitney": {"U": mw.statistic, "p": mw.pvalue},
        "d_cohen": cohen_d(a, b),
        "d_cohen_log": cohen_d(np.log(a), np.log(b)),
        "prob_superioridade": prob_superioridade(a, b),
        "concordam": bool((welch.pvalue < ALFA) == (mw.pvalue < ALFA)),
    }


if __name__ == "__main__":
    dados = gerar_dados(seed=42)
    com_bot, sem_bot = dados["com_bot"], dados["sem_bot"]
    print(f"Mediana com_bot: {np.median(com_bot):.2f} h | média: {com_bot.mean():.2f} h")
    print(f"Mediana sem_bot: {np.median(sem_bot):.2f} h | média: {sem_bot.mean():.2f} h")
    r = aplicar_testes(com_bot, sem_bot)
    w, m = r["welch"], r["mann_whitney"]
    print(f"Welch: t = {w['t']:.3f}, gl = {w['gl']:.1f}, p = {w['p']:.4f}")
    print(f"Mann-Whitney: U = {m['U']:.1f}, p = {m['p']:.4f}")
    print(f"d de Cohen (horas): {r['d_cohen']:.3f} | (log das horas): {r['d_cohen_log']:.3f}")
    print(f"P(com_bot > sem_bot): {r['prob_superioridade']:.3f}")
    print(f"Concordam em alfa = {ALFA}: {r['concordam']}")
