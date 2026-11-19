"""Pipeline de análise: CSV por passo -> tabelas e figuras.

    python -m analysis.run --sintetico                  # dados sintéticos
    python -m analysis.run --entrada data/pilot/passos.csv   # dados do piloto/coleta

O formato do CSV é o mesmo nos dois casos (analysis/schema.py).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from analysis import models, pilot, survival
from analysis.schema import carregar, validar
from analysis.synthetic import gerar

RAIZ = Path(__file__).resolve().parent.parent
CORES = {"incremental": "#c0392b", "regenerado": "#2c6fbb"}


def _figuras(df, km, saida: Path) -> None:
    taxa = models.taxa_de_regressao(df)
    fig, ax = plt.subplots(figsize=(6, 4))
    for modo, g in taxa.groupby("mode"):
        m = g.groupby("step")["taxa"].mean()
        ax.plot(m.index, m.values * 100, marker="o", label=modo, color=CORES[modo])
    ax.set_xlabel("passo"); ax.set_ylabel("regressão média (% dos testes)"); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(saida / "regressao_por_passo.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for modo, g in km.groupby("mode"):
        ax.step(g["tempo"], g["sobrevivencia"], where="post", label=modo, color=CORES[modo])
        ax.fill_between(g["tempo"], g["ic_inf"], g["ic_sup"], step="post", alpha=0.15, color=CORES[modo])
    ax.set_xlabel("passo"); ax.set_ylabel("P(sem regressão até o passo)"); ax.set_ylim(0, 1.02); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(saida / "kaplan_meier.png", dpi=150); plt.close(fig)


def analisar(df: pd.DataFrame, saida: Path) -> dict[str, pd.DataFrame]:
    saida.mkdir(parents=True, exist_ok=True)
    out: dict[str, pd.DataFrame] = {}

    descritiva = (
        df[df["step"] >= 1].assign(taxa=lambda d: d["reg_failed"].astype(float) / d["reg_total"].astype(float))
        .groupby(["mode", "step"])
        .agg(cadeias=("chain_id", "nunique"), taxa_regressao=("taxa", "mean"), arch_violations=("arch_violations", "mean"),
             files_touched=("files_touched", "mean"), dup_pct=("dup_pct", "mean"), max_ccn=("max_ccn", "mean"),
             doc_drift=("doc_drift", "mean"))
        .reset_index()
    )
    out["descritiva"] = descritiva

    glmm = models.glmm_regressao(df)
    sens = models.glmm_sensibilidade(df)
    out["glmm"], out["glmm_sensibilidade"] = glmm, sens

    t = survival.tempos_ate_regressao(df)
    km = pd.concat([survival.kaplan_meier(g["tempo"], g["evento"]).assign(mode=m) for m, g in t.groupby("mode")])
    qui, p_lr = survival.log_rank(t["tempo"], t["evento"], t["mode"])
    out["kaplan_meier"] = km
    out["log_rank"] = pd.DataFrame([{"qui_quadrado": qui, "gl": 1, "p": p_lr, "cadeias": len(t), "eventos": int(t["evento"].sum())}])

    crescimento = pd.concat([models.curva_de_crescimento(df, d) for d in ("arch_violations", "files_touched", "dup_pct")])
    out["crescimento"] = crescimento
    out["h5_tipo_de_pedido"] = models.efeito_tipo_de_pedido(df)
    pareada = models.diferenca_pareada(df)
    out["diferenca_pareada"] = pareada
    var = models.variancia_entre_cadeias(df)
    out["variancia_entre_cadeias"] = var
    out["h3_tendencia"] = var.attrs["tendencia"]

    # Holm sobre a família confirmatória: uma linha por hipótese/teste do plano.
    familia = [
        ("H1", "GLMM: inclinação do passo (regenerado)", glmm.loc[glmm["termo"] == "step", "p"].iloc[0]),
        ("H4", "GLMM: interação modo × passo", glmm.loc[glmm["termo"] == "inc:step", "p"].iloc[0]),
        ("H4", "log-rank: passo da 1ª regressão", p_lr),
        ("H2", "crescimento files_touched: modo × passo", crescimento[(crescimento["desfecho"] == "files_touched") & (crescimento["termo"] == "inc:step")]["p"].iloc[0]),
        ("H2", "crescimento dup_pct: modo × passo", crescimento[(crescimento["desfecho"] == "dup_pct") & (crescimento["termo"] == "inc:step")]["p"].iloc[0]),
        ("H5", "GLMM: pedido que tensiona (regressão)", out["h5_tipo_de_pedido"].iloc[0]["p"]),
        ("H5", "misto: pedido que tensiona (violações novas)", out["h5_tipo_de_pedido"].iloc[1]["p"]),
        ("H3", "variância entre cadeias × passo (incremental)", out["h3_tendencia"].set_index("mode")["p"].get("incremental", float("nan"))),
    ] + [("Extra", f"Wilcoxon pareado, passo {int(r.passo)}", r.wilcoxon_p) for r in pareada.itertuples()]
    out["testes_holm"] = models.holm(pd.DataFrame(familia, columns=["hipotese", "teste", "p"]))

    for nome, tabela in out.items():
        tabela.to_csv(saida / f"{nome}.csv", index=False)
    _figuras(df, km, saida)
    return out


def principal(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Pipeline de análise do Lab05.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sintetico", action="store_true", help="gera e analisa dados sintéticos")
    g.add_argument("--entrada", type=Path, help="CSV por passo (piloto ou coleta completa)")
    ap.add_argument("--cadeias", type=int, default=12, help="cadeias por modo no sintético")
    ap.add_argument("--saida", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.sintetico:
        df = gerar(args.cadeias)
        pasta_dados = RAIZ / "data" / "synthetic"
        pasta_dados.mkdir(parents=True, exist_ok=True)
        df.to_csv(pasta_dados / "passos_sintetico.csv", index=False)
        saida = args.saida or RAIZ / "results" / "sintetico"
    else:
        df = carregar(args.entrada)
        saida = args.saida or RAIZ / "results" / args.entrada.stem
    erros = validar(df)
    if erros:
        raise SystemExit("CSV inválido:\n - " + "\n - ".join(erros))
    out = analisar(df, saida)
    print(f"{len(df)} linhas, {df.groupby(['chain_id', 'mode']).ngroups} cadeias-modo. Saídas em {saida}")
    print(out["testes_holm"].round(4).to_string(index=False))


if __name__ == "__main__":
    principal()
