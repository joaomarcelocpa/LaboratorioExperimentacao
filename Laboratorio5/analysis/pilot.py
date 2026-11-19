"""Critérios do piloto (PLANEJAMENTO.pdf, 3.12) calculados a partir do CSV por passo.

Cada critério devolve PASSA, FALHA ou PENDENTE (falta uma informação que é
decisão do grupo, como o orçamento) com o valor observado. A decisão final é
do grupo; `sugerir_decisao` aplica uma regra simples só para dar um ponto de
partida, e o relatório deve justificar a decisão com os dados.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis.survival import tempos_ate_regressao

LIMITE_EXECUCAO = 0.95


@dataclass(frozen=True)
class Criterio:
    nome: str
    resultado: str  # PASSA | FALHA | PENDENTE
    valor: str
    regra: str


def _execucoes(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["step"] >= 1]


def execucao_do_agente(df: pd.DataFrame) -> Criterio:
    e = _execucoes(df)
    sucesso = ((e["retry"] == 0) & (e["run_ok"] == 1)).mean() if len(e) else np.nan
    return Criterio(
        "Execução do agente", "PASSA" if sucesso > LIMITE_EXECUCAO else "FALHA",
        f"{sucesso:.1%} de {len(e)} execuções sem erro nem tempo esgotado na 1ª tentativa",
        "> 95% das execuções sem erro nem tempo esgotado (1ª tentativa)",
    )


def determinismo(df: pd.DataFrame) -> Criterio:
    e = _execucoes(df)[lambda x: x["status"] == "ok"]
    instaveis = int((e["flaky"].fillna(0) > 0).sum())
    return Criterio(
        "Determinismo dos testes", "PASSA" if instaveis == 0 else "FALHA",
        f"{instaveis} de {len(e)} passos com teste instável (flaky > 0)",
        "duas rodadas no mesmo código dão o mesmo resultado (flaky = 0 em todos os passos)",
    )


def sem_piso_nem_teto(df: pd.DataFrame) -> Criterio:
    """Piso: nenhuma regressão nem violação. Teto: em algum modo, todas as cadeias já
    regridem ou quebram até o passo 2. (Interpretação do grupo a confirmar.)"""
    e = _execucoes(df)[lambda x: x["status"] == "ok"]
    ocorrencias = int(((e["reg_failed"] > 0) | (e["arch_violations"] > 0)).sum())
    t = tempos_ate_regressao(df)
    falhas = df[df["status"] == "falha"].groupby(["chain_id", "mode"])["step"].min()
    teto = []
    for modo, g in t.groupby("mode"):
        quebrou = 0
        for _, r in g.iterrows():
            passo_falha = falhas.get((r["chain_id"], modo), np.inf)
            if (r["evento"] == 1 and r["tempo"] <= 2) or passo_falha <= 2:
                quebrou += 1
        if quebrou == len(g):
            teto.append(modo)
    piso = ocorrencias == 0
    return Criterio(
        "Sem piso nem teto", "PASSA" if not piso and not teto else "FALHA",
        f"{ocorrencias} passos com regressão ou violação" + (f"; teto no modo {', '.join(teto)}" if teto else ""),
        "há regressões ou violações, mas as cadeias não quebram já no passo 2",
    )


def variacao_entre_cadeias(df: pd.DataFrame) -> Criterio:
    d = _execucoes(df)[lambda x: x["status"] == "ok"].copy()
    d["taxa"] = d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    por_cadeia = d.groupby(["mode", "chain_id"])["taxa"].mean()
    desvios = por_cadeia.groupby("mode").std(ddof=1)
    maior = float(desvios.max()) if len(desvios) else np.nan
    ok = bool(np.isfinite(maior) and maior > 0)
    texto = ", ".join(f"{m}: dp {v:.4f}" for m, v in desvios.items())
    return Criterio(
        "Variação entre cadeias", "PASSA" if ok else "FALHA", f"dp entre cadeias da taxa média de regressão ({texto})",
        "variação entre cadeias maior que zero em algum modo, base para estimar o poder",
    )


def custo_e_tempo(df: pd.DataFrame, orcamento_usd_cadeia: float | None = None, limite_horas_cadeia: float | None = None) -> Criterio:
    e = _execucoes(df)
    custo = e.groupby(["mode", "chain_id"])["cost_usd"].sum()
    horas = e.groupby(["mode", "chain_id"])["duration_s"].sum() / 3600
    passos = e.groupby(["mode", "chain_id"])["step"].count()
    # extrapola para 10 passos pelo custo médio por passo
    custo10 = float((custo / passos * 10).mean()) if len(custo) else np.nan
    horas10 = float((horas / passos * 10).mean()) if len(horas) else np.nan
    valor = f"≈ US$ {custo10:.2f} e {horas10:.2f} h por cadeia de 10 passos (extrapolado do piloto)"
    if orcamento_usd_cadeia is None and limite_horas_cadeia is None:
        return Criterio("Custo e tempo", "PENDENTE", valor, "dentro do orçamento ou dos limites de uso e de tempo (orçamento ainda não definido)")
    dentro = True
    if orcamento_usd_cadeia is not None:
        dentro &= custo10 <= orcamento_usd_cadeia
    if limite_horas_cadeia is not None:
        dentro &= horas10 <= limite_horas_cadeia
    return Criterio("Custo e tempo", "PASSA" if dentro else "FALHA", valor, "dentro do orçamento ou dos limites de uso e de tempo")


def avaliar(df: pd.DataFrame, orcamento_usd_cadeia: float | None = None, limite_horas_cadeia: float | None = None) -> list[Criterio]:
    return [
        execucao_do_agente(df), determinismo(df), sem_piso_nem_teto(df),
        variacao_entre_cadeias(df), custo_e_tempo(df, orcamento_usd_cadeia, limite_horas_cadeia),
    ]


def sugerir_decisao(criterios: list[Criterio]) -> str:
    """Ponto de partida, não a decisão: 0 falhas = GO; 3+ falhas, ou falha de execução e de custo
    juntas = NO-GO; qualquer outro caso = GO com ajustes. Pendências impedem concluir."""
    if any(c.resultado == "PENDENTE" for c in criterios):
        return "INDEFINIDA (há critério PENDENTE)"
    falhas = {c.nome for c in criterios if c.resultado == "FALHA"}
    if not falhas:
        return "GO"
    if len(falhas) >= 3 or {"Execução do agente", "Custo e tempo"} <= falhas:
        return "NO-GO"
    return "GO com ajustes"


def tabela_markdown(criterios: list[Criterio]) -> str:
    linhas = ["| Critério | Resultado | Valor observado | Passa quando |", "|---|---|---|---|"]
    linhas += [f"| {c.nome} | {c.resultado} | {c.valor} | {c.regra} |" for c in criterios]
    return "\n".join(linhas)


def principal(argv=None) -> None:
    import argparse
    from pathlib import Path

    from analysis.schema import carregar, validar

    ap = argparse.ArgumentParser(description="Avalia os 5 critérios do piloto (seção 3.12) a partir do CSV por passo.")
    ap.add_argument("entrada", type=Path)
    ap.add_argument("--orcamento-usd-cadeia", type=float, default=None)
    ap.add_argument("--limite-horas-cadeia", type=float, default=None)
    args = ap.parse_args(argv)
    df = carregar(args.entrada)
    erros = validar(df)
    if erros:
        raise SystemExit("CSV inválido:\n - " + "\n - ".join(erros))
    criterios = avaliar(df, args.orcamento_usd_cadeia, args.limite_horas_cadeia)
    print(tabela_markdown(criterios))
    print(f"\nSugestão de decisão (ponto de partida, não a decisão): {sugerir_decisao(criterios)}")


if __name__ == "__main__":
    principal()
