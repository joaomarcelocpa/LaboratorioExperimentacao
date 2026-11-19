"""Gerador de dados sintéticos no formato do CSV por passo.

Serve para o pipeline funcionar antes do piloto existir. Todos os parâmetros
abaixo são SUPOSIÇÕES de trabalho, não resultados: serão substituídos por
estimativas do piloto (ver analysis/pilot.py e analysis/power.py --piloto).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from analysis.schema import NOMES, PASSO_MAX

# Tipo de cada pedido: P1 a P4 vêm do piloto; P5 a P10 são provisórios (S02).
TIPO_DO_PEDIDO = {
    1: "cabe", 2: "cabe", 3: "tensiona", 4: "cabe",
    5: "cabe", 6: "tensiona", 7: "cabe", 8: "tensiona", 9: "cabe", 10: "tensiona",
}


@dataclass(frozen=True)
class Parametros:
    """Processo gerador da regressão e das métricas estruturais."""

    p_base: float = 0.005         # taxa de regressão no passo 0, modo regenerado
    sd_cadeia: float = 0.5        # desvio-padrão do efeito aleatório da cadeia (logit)
    inclinacao_regen: float = 0.03   # logit por passo no modo regenerado (linha de base)
    inclinacao_extra_inc: float = 0.15  # logit extra por passo no modo incremental
    efeito_tensiona: float = 0.5  # logit extra quando o pedido tensiona a arquitetura
    reg_total_base: int = 40
    reg_total_por_passo: int = 6  # a suíte de regressão cresce com os pedidos aceitos
    cadeia_compartilhada: bool = False  # True: a cadeia i tem o mesmo efeito nos dois modos (pareamento real)
    p_falha_execucao: float = 0.03
    p_agente_roda_testes: float = 0.6
    versao: str = "sintetico"
    modelo: str = "claude-sonnet-5-5"
    extras: dict = field(default_factory=dict)

    def com(self, **kw) -> "Parametros":
        return replace(self, **kw)


def _expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p):
    return np.log(p / (1 - p))


def probabilidade_regressao(par: Parametros, modo: str, passo, efeito_cadeia, tensiona) -> np.ndarray:
    """P(um teste de regressão falha) no passo, para uma cadeia (vetorizável)."""
    inc = 1.0 if modo == "incremental" else 0.0
    eta = (
        _logit(par.p_base)
        + efeito_cadeia
        + (par.inclinacao_regen + inc * par.inclinacao_extra_inc) * np.asarray(passo, dtype=float)
        + par.efeito_tensiona * np.asarray(tensiona, dtype=float)
    )
    return _expit(eta)


def gerar(
    n_cadeias: int = 12,
    passos: int = PASSO_MAX,
    parametros: Parametros | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Gera o CSV por passo (todas as colunas do esquema, na ordem) para n cadeias × 2 modos."""
    par = parametros or Parametros()
    rng = np.random.default_rng(seed)
    linhas: list[dict] = []
    inicio = pd.Timestamp("2026-12-01T09:00:00Z")
    relogio = 0

    for cadeia in range(1, n_cadeias + 1):
        u_comum = rng.normal(0, par.sd_cadeia)
        for modo in ("incremental", "regenerado"):
            u = u_comum if par.cadeia_compartilhada else rng.normal(0, par.sd_cadeia)
            viol = 0
            ccn = 6
            for passo in range(0, passos + 1):
                tipo = "semente" if passo == 0 else TIPO_DO_PEDIDO[passo]
                tens = 1 if tipo == "tensiona" else 0
                relogio += int(rng.integers(120, 900))
                linha = dict.fromkeys(NOMES)
                linha.update(
                    chain_id=cadeia, mode=modo, step=passo, request_id=f"P{passo}",
                    request_type=tipo,
                    timestamp=(inicio + pd.Timedelta(seconds=relogio)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    tool_version=par.versao, model_id=par.modelo,
                    retry=0, run_ok=1, status="ok",
                )
                reg_total = par.reg_total_base + par.reg_total_por_passo * passo
                if passo == 0:
                    linha.update(
                        build_ok=1, boot_ok=1, reg_total=reg_total, reg_failed=0,
                        acc_total=0, acc_failed=0, flaky=0, arch_violations=0, cycles=0,
                        files_touched=0, modules_touched=0, max_ccn=ccn, dup_pct=1.0,
                        loc=int(rng.integers(600, 1000)), doc_drift=0,
                    )
                    linhas.append(linha)
                    continue

                # execução do agente, com uma nova tentativa se falhar
                falhou1 = rng.random() < par.p_falha_execucao
                falhou2 = falhou1 and rng.random() < par.p_falha_execucao
                linha["retry"] = int(falhou1)
                linha["run_ok"] = int(not falhou2)
                turns = int(rng.integers(8, 40))
                linha.update(
                    turns=turns,
                    tokens_in=int(rng.lognormal(12.0, 0.4)),
                    tokens_out=int(rng.lognormal(9.5, 0.4)),
                    cost_usd=round(float(rng.lognormal(-0.8, 0.5)), 4),
                    duration_s=round(float(rng.lognormal(5.3, 0.4)), 1),
                    agent_ran_tests=int(rng.random() < par.p_agente_roda_testes),
                )
                if falhou2:
                    linha.update(status="falha", build_ok=0)
                    linhas.append(linha)
                    break  # a cadeia termina

                p = probabilidade_regressao(par, modo, passo, u, tens)
                reg_failed = int(rng.binomial(reg_total, p))
                acc_total = int(rng.integers(3, 7))
                acc_failed = int(rng.binomial(acc_total, 0.08 + 0.1 * tens))
                flaky = int(rng.random() < 0.02)

                if modo == "incremental":
                    viol += int(rng.poisson(0.15 + 0.5 * tens))
                    arquivos = 2 + int(rng.poisson(1.0 + 0.3 * passo))
                    ccn = max(4, ccn + int(rng.integers(-1, 3)))
                    dup = 1.0 + 0.3 * passo + abs(rng.normal(0, 0.4))
                    drift = int(rng.poisson(0.1 * passo))
                else:
                    viol = int(rng.poisson(0.4 + 0.05 * passo))
                    arquivos = 8 + int(rng.poisson(2.0 + 0.2 * passo))
                    ccn = max(4, int(rng.normal(8 + 0.2 * passo, 1.5)))
                    dup = 1.0 + 0.1 * passo + abs(rng.normal(0, 0.4))
                    drift = int(rng.poisson(0.2))
                modulos = int(min(arquivos, 1 + rng.binomial(4, 0.35 + 0.05 * tens)))
                linha.update(
                    build_ok=1, boot_ok=1, reg_total=reg_total, reg_failed=reg_failed,
                    acc_total=acc_total, acc_failed=acc_failed, flaky=flaky,
                    arch_violations=viol, cycles=int(rng.poisson(0.1 * viol)),
                    files_touched=arquivos, modules_touched=modulos, max_ccn=ccn,
                    dup_pct=round(float(dup), 2), loc=int(700 + 90 * passo + rng.normal(0, 40)),
                    doc_drift=drift,
                )
                linhas.append(linha)
    df = pd.DataFrame(linhas, columns=NOMES)
    return df
