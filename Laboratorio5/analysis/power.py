"""Simulação de poder para definir o número de cadeias por modo.

Reaproveita o desenho do Lab04 (Monte Carlo com default_rng(42), proporção de
p < alfa por teste, Welch × Mann-Whitney), trocando o gerador lognormal pelo
processo gerador da regressão por cadeia (analysis/synthetic.py).

Resumo por cadeia: taxa média de regressão nos passos 1..10 (um número por
cadeia e modo). Testes comparados, todos bicaudais, alfa = 0,05:
  - Welch e Mann-Whitney (cadeias independentes entre modos, o padrão; com
    `cadeia_compartilhada` esses dois ficam conservadores e vale o pareado);
  - Wilcoxon pareado por chain_id (válido também se o pareamento for arbitrário);
  - log-rank do passo da primeira regressão.
O modelo final (GLMM) usa os dados por passo e deve ter mais poder que este
resumo por cadeia; o número de cadeias daqui é, portanto, conservador.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from analysis.survival import log_rank
from analysis.synthetic import Parametros, TIPO_DO_PEDIDO, probabilidade_regressao

ALFA = 0.05
SEMENTE = 42
REPETICOES = 2000
GRADE_CADEIAS = (3, 5, 8, 10, 12, 15, 20)
ALVO_PODER = 0.80
PASSOS = 10

# Cenários de efeito: o quanto o incremental degrada além do regenerado (logit por passo).
CENARIOS = {"pequeno": 0.05, "medio": 0.10, "grande": 0.20}

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "results" / "power"


def _simular_regressoes(par: Parametros, k: int, reps: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """Contagens de regressão e totais, formato (reps, k, passos) por modo."""
    passos = np.arange(1, PASSOS + 1)
    tens = np.array([1 if TIPO_DO_PEDIDO[p] == "tensiona" else 0 for p in passos])
    total = par.reg_total_base + par.reg_total_por_passo * passos
    u = rng.normal(0, par.sd_cadeia, size=(reps, k))
    out = {}
    for modo in ("incremental", "regenerado"):
        if modo == "regenerado" and not par.cadeia_compartilhada:
            u = rng.normal(0, par.sd_cadeia, size=(reps, k))  # cadeias independentes entre modos
        p = probabilidade_regressao(par, modo, passos[None, None, :], u[:, :, None], tens[None, None, :])
        out[modo] = rng.binomial(total[None, None, :], p)
    return out["incremental"], out["regenerado"], total


def _tempo_evento(contagens: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Passo da primeira regressão (1..10) e evento; sem regressão = censurado em 10."""
    houve = contagens > 0
    evento = houve.any(axis=-1)
    primeiro = np.where(evento, houve.argmax(axis=-1) + 1, PASSOS)
    return primeiro, evento.astype(int)


def poder(par: Parametros, k: int, reps: int = REPETICOES, seed: int = SEMENTE, alfa: float = ALFA) -> dict[str, float]:
    """Proporção de rejeições de H0 de cada teste, com k cadeias por modo."""
    rng = np.random.default_rng(seed)
    inc, reg, total = _simular_regressoes(par, k, reps, rng)
    taxa_inc = (inc / total).mean(axis=-1)  # (reps, k)
    taxa_reg = (reg / total).mean(axis=-1)

    p_welch = stats.ttest_ind(taxa_inc, taxa_reg, axis=1, equal_var=False).pvalue
    p_mw = stats.mannwhitneyu(taxa_inc, taxa_reg, axis=1, alternative="two-sided").pvalue
    dif = taxa_inc - taxa_reg
    p_wil = np.ones(reps)
    for i in range(reps):
        if (dif[i] != 0).any():
            p_wil[i] = stats.wilcoxon(dif[i], zero_method="wilcox").pvalue

    t_inc, e_inc = _tempo_evento(inc)
    t_reg, e_reg = _tempo_evento(reg)
    grupo = np.array([0] * k + [1] * k)
    p_lr = np.empty(reps)
    for i in range(reps):
        _, p_lr[i] = log_rank(np.concatenate([t_inc[i], t_reg[i]]), np.concatenate([e_inc[i], e_reg[i]]), grupo)

    return {
        "welch": float(np.nanmean(p_welch < alfa)),
        "mann_whitney": float(np.mean(p_mw < alfa)),
        "wilcoxon_pareado": float(np.mean(p_wil < alfa)),
        "log_rank": float(np.mean(p_lr < alfa)),
    }


def margem_de_erro(p: float, reps: int) -> float:
    return float(1.96 * np.sqrt(p * (1 - p) / reps))


def tabela_de_poder(par: Parametros, grade=GRADE_CADEIAS, reps: int = REPETICOES, seed: int = SEMENTE) -> pd.DataFrame:
    linhas = []
    for nome, extra in CENARIOS.items():
        cenario = par.com(inclinacao_extra_inc=extra)
        for k in grade:
            for teste, valor in poder(cenario, k, reps, seed).items():
                linhas.append({
                    "cenario": nome, "efeito_extra_logit_por_passo": extra, "cadeias_por_modo": k,
                    "teste": teste, "poder": valor, "margem_erro_95": margem_de_erro(valor, reps), "repeticoes": reps,
                })
    return pd.DataFrame(linhas)


def erro_tipo_i(par: Parametros, k: int = 10, reps: int = REPETICOES, seed: int = SEMENTE) -> dict[str, float]:
    """Calibração: com efeito extra zero, a taxa de rejeição deve ficar perto de alfa."""
    return poder(par.com(inclinacao_extra_inc=0.0), k, reps, seed)


def cadeias_necessarias(tabela: pd.DataFrame, cenario: str = "medio", teste: str = "welch", alvo: float = ALVO_PODER) -> int | None:
    """Menor número de cadeias por modo da grade que atinge o poder-alvo; None se nenhum atinge."""
    t = tabela[(tabela["cenario"] == cenario) & (tabela["teste"] == teste) & (tabela["poder"] >= alvo)]
    return int(t["cadeias_por_modo"].min()) if len(t) else None


def estimar_parametros_do_piloto(df: pd.DataFrame, base: Parametros | None = None) -> Parametros:
    """Troca as suposições pelas estimativas do piloto (aproximadas, com poucas cadeias).

    p_base: taxa de regressão média no modo regenerado; inclinação extra: diferença
    entre as inclinações logit-por-passo dos dois modos (regressão linear nas taxas
    suavizadas); sd_cadeia: desvio-padrão do logit da taxa média por cadeia.
    """
    par = base or Parametros()
    d = df[(df["step"] >= 1) & (df["status"] == "ok")].copy()
    d["taxa"] = (d["reg_failed"].astype(float) + 0.5) / (d["reg_total"].astype(float) + 1.0)
    d["logit"] = np.log(d["taxa"] / (1 - d["taxa"]))
    inc = {"incremental": 1.0, "regenerado": 0.0}
    inclinacao = {}
    for modo, g in d.groupby("mode"):
        inclinacao[modo] = float(np.polyfit(g["step"].astype(float), g["logit"], 1)[0]) if g["step"].nunique() > 1 else 0.0
    reg = d[d["mode"] == "regenerado"]
    p_base = float(np.clip(reg["taxa"].mean(), 0.001, 0.5)) if len(reg) else par.p_base
    por_cadeia = d.groupby(["chain_id", "mode"])["logit"].mean().groupby("mode").std(ddof=1)
    sd = float(np.nanmean(por_cadeia.values)) if len(por_cadeia) else par.sd_cadeia
    extra = inclinacao.get("incremental", 0.0) - inclinacao.get("regenerado", 0.0)
    return par.com(
        p_base=p_base,
        sd_cadeia=max(sd, 0.05) if np.isfinite(sd) else par.sd_cadeia,
        inclinacao_regen=inclinacao.get("regenerado", par.inclinacao_regen),
        inclinacao_extra_inc=float(extra),
    )


def principal(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Simulação de poder (número de cadeias por modo).")
    ap.add_argument("--repeticoes", type=int, default=REPETICOES)
    ap.add_argument("--piloto", type=Path, help="CSV do piloto: estima os parâmetros em vez de usar as suposições")
    ap.add_argument("--saida", type=Path, default=SAIDA)
    args = ap.parse_args(argv)

    par = Parametros()
    if args.piloto:
        from analysis.schema import carregar
        par = estimar_parametros_do_piloto(carregar(args.piloto))
    args.saida.mkdir(parents=True, exist_ok=True)
    tab = tabela_de_poder(par, reps=args.repeticoes)
    tab.to_csv(args.saida / "poder.csv", index=False)
    erro1 = erro_tipo_i(par, reps=args.repeticoes)
    pd.Series(erro1, name="erro_tipo_i").to_csv(args.saida / "erro_tipo_i.csv")
    (args.saida / "parametros.txt").write_text(repr(par) + "\n")
    for cen in CENARIOS:
        print(f"{cen:8s}: cadeias por modo (poder >= {ALVO_PODER:.0%}, Welch) = {cadeias_necessarias(tab, cen)}")
    print("erro tipo I (k=10):", {k: round(v, 3) for k, v in erro1.items()})


if __name__ == "__main__":
    principal()
