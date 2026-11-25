"""Pipeline de análise: CSV por passo -> tabelas e figuras.

    python -m analysis.run --sintetico                  # dados sintéticos
    python -m analysis.run --entrada data/pilot/passos.csv   # dados do piloto/coleta

O formato do CSV é o mesmo nos dois casos (analysis/schema.py). Saídas:

    <saida>/descritiva/         tabelas por modo, passo e tipo de pedido (#123)
    <saida>/figures/            gráficos (#123 e #125)
    <saida>/modelos/            GLMM, curvas de crescimento, H3 e H5 (#124)
    <saida>/sobrevivencia/      Kaplan-Meier, log-rank e sensibilidade à censura (#125)
    <saida>/diferenca-pareada/  Wilcoxon pareado e delta de Cliff com IC (#125)
    <saida>/testes_holm.csv     família confirmatória com p e p de Holm (#125)

Na coleta completa, `--saida results` grava direto em results/descritiva etc.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from analysis import descritiva, figuras, models, survival
from analysis.schema import carregar, validar
from analysis.synthetic import gerar

RAIZ = Path(__file__).resolve().parent.parent

# Subpasta de cada tabela dentro da pasta de saída (issues #123, #124 e #125).
PASTAS = {
    "resumo_da_coleta": "descritiva", "por_passo": "descritiva", "por_passo_completa": "descritiva",
    "por_tipo_de_pedido": "descritiva",
    "glmm": "modelos", "glmm_sensibilidade": "modelos", "crescimento": "modelos",
    "h5_tipo_de_pedido": "modelos", "variancia_entre_cadeias": "modelos", "h3_tendencia": "modelos",
    "tempos_ate_regressao": "sobrevivencia", "kaplan_meier": "sobrevivencia", "log_rank": "sobrevivencia",
    "log_rank_sensibilidade": "sobrevivencia",
    "diferenca_pareada": "diferenca-pareada",
    "testes_holm": ".",
}


def _sobrevivencia(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sens = []
    for tratamento in survival.TRATAMENTOS_DA_FALHA:
        t = survival.tempos_ate_regressao(df, falha=tratamento)
        qui, p = survival.log_rank(t["tempo"], t["evento"], t["mode"])
        sens.append({"falha_tratada_como": tratamento, "qui_quadrado": qui, "gl": 1, "p": p,
                     "cadeias": len(t), "eventos": int(t["evento"].sum())})
        if tratamento == "censura":
            principal_t, principal_p, principal_q = t, p, qui
    km = pd.concat([survival.kaplan_meier(g["tempo"], g["evento"]).assign(mode=m) for m, g in principal_t.groupby("mode")])
    return {
        "tempos_ate_regressao": principal_t,
        "kaplan_meier": km,
        "log_rank": pd.DataFrame([{"qui_quadrado": principal_q, "gl": 1, "p": principal_p, "cadeias": len(principal_t),
                                   "eventos": int(principal_t["evento"].sum())}]),
        "log_rank_sensibilidade": pd.DataFrame(sens),
    }


def analisar(df: pd.DataFrame, saida: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = dict(descritiva.tabelas(df))

    glmm = models.glmm_regressao(df)
    out["glmm"], out["glmm_sensibilidade"] = glmm, models.glmm_sensibilidade(df)

    out.update(_sobrevivencia(df))
    p_lr = float(out["log_rank"]["p"].iloc[0])

    crescimento = pd.concat([models.curva_de_crescimento(df, d) for d in ("arch_violations", "files_touched", "dup_pct")])
    out["crescimento"] = crescimento
    out["h5_tipo_de_pedido"] = models.efeito_tipo_de_pedido(df)
    pareada = models.diferenca_pareada(df)
    out["diferenca_pareada"] = pareada
    var = models.variancia_entre_cadeias(df)
    out["variancia_entre_cadeias"] = var
    out["h3_tendencia"] = var.attrs["tendencia"]

    # Holm sobre a família confirmatória, declarada no plano de análise antes dos dados.
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
        pasta = saida / PASTAS[nome]
        pasta.mkdir(parents=True, exist_ok=True)
        tabela.to_csv(pasta / f"{nome}.csv", index=False)
    figuras.todas(df, out["kaplan_meier"], pareada, saida / "figures")
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
