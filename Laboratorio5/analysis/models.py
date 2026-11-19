"""Modelos do plano de análise (PLANEJAMENTO.pdf, seção 3.9).

H1/H4  GLMM binomial: regressão ~ modo × passo, cadeia como efeito aleatório.
H2/H5  Modelo misto de curva de crescimento (inclinação aleatória por cadeia).
H3     Variância entre cadeias por passo.
Extra  Diferença incremental − regenerado no mesmo passo (Wilcoxon pareado,
       delta de Cliff) e correção de Holm.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests


def _passos_validos(df: pd.DataFrame) -> pd.DataFrame:
    """Passos 1..10 com execução concluída (status ok)."""
    d = df[(df["step"] >= 1) & (df["status"] == "ok")].copy()
    for c in ("reg_total", "reg_failed", "step", "chain_id"):
        d[c] = d[c].astype(int)
    d["inc"] = (d["mode"] == "incremental").astype(int)
    d["tensiona"] = (d["request_type"] == "tensiona").astype(int)
    return d


def expandir_testes(d: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por teste de regressão executado (y = 1 se falhou)."""
    repete = d["reg_total"].to_numpy()
    base = d.loc[d.index.repeat(repete), ["chain_id", "mode", "inc", "step", "tensiona"]].reset_index(drop=True)
    y = np.zeros(len(base), dtype=int)
    fim = np.cumsum(repete)
    ini = fim - repete
    for i, k in enumerate(d["reg_failed"].to_numpy()):
        y[ini[i]: ini[i] + k] = 1
    base["y"] = y
    return base


def _or_table(nome, estimativa, erro) -> dict:
    return {
        "termo": nome, "coef": estimativa, "erro_padrao": erro,
        "odds_ratio": float(np.exp(estimativa)),
        "ic95_inf": float(np.exp(estimativa - 1.96 * erro)),
        "ic95_sup": float(np.exp(estimativa + 1.96 * erro)),
        "p": float(2 * stats.norm.sf(abs(estimativa / erro))) if erro > 0 else np.nan,
    }


def glmm_regressao(df: pd.DataFrame, formula_fixa: str = "y ~ inc * step") -> pd.DataFrame:
    """GLMM binomial com intercepto aleatório por cadeia (Bayes variacional).

    statsmodels não traz GLMM por máxima verossimilhança; BinomialBayesMixedGLM
    ajusta o mesmo modelo por aproximação variacional. Os "IC 95%" são
    intervalos de credibilidade aproximados (média ± 1,96 dp a posteriori) e
    tendem a ser estreitos; por isso `glmm_sensibilidade` confere com GEE.
    """
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    t = expandir_testes(_passos_validos(df))
    t["cadeia"] = t["chain_id"].astype(str)
    modelo = BinomialBayesMixedGLM.from_formula(formula_fixa, {"cadeia": "0 + C(cadeia)"}, t)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = modelo.fit_vb()
    linhas = [
        _or_table(nome, res.fe_mean[i], res.fe_sd[i])
        for i, nome in enumerate(modelo.exog_names)
    ]
    out = pd.DataFrame(linhas)
    out["sd_cadeia_logit"] = float(np.exp(res.vcp_mean[0]))
    return out


def glmm_sensibilidade(df: pd.DataFrame, formula_fixa: str = "y ~ inc * step") -> pd.DataFrame:
    """Mesma pergunta via GEE (correlação intra-cadeia permutável), erros robustos."""
    t = expandir_testes(_passos_validos(df))
    modelo = smf.gee(formula_fixa, groups="chain_id", data=t, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = modelo.fit()
    return pd.DataFrame([_or_table(n, res.params[n], res.bse[n]) for n in res.params.index])


def curva_de_crescimento(df: pd.DataFrame, desfecho: str) -> pd.DataFrame:
    """Modelo misto: desfecho ~ modo × passo, intercepto e inclinação aleatórios por cadeia.

    Se a inclinação aleatória não converge (poucas cadeias), cai para só
    intercepto aleatório e marca `modelo` na saída.
    """
    d = df[df["status"] == "ok"].copy()
    d = d[d[desfecho].notna()]
    d[desfecho] = d[desfecho].astype(float)
    d["step"] = d["step"].astype(int)
    d["chain_id"] = d["chain_id"].astype(int)
    d["inc"] = (d["mode"] == "incremental").astype(int)
    formula = f"{desfecho} ~ inc * step"
    resultado, tipo = None, ""
    for re_formula, rotulo in (("~step", "intercepto+inclinação"), ("~1", "intercepto")):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = smf.mixedlm(formula, d, groups=d["chain_id"], re_formula=re_formula)
                r = m.fit(method="lbfgs", reml=True)
            if np.isfinite(r.bse_fe).all():
                resultado, tipo = r, rotulo
                break
        except Exception:
            continue
    if resultado is None:
        raise RuntimeError(f"curva de crescimento de {desfecho} não convergiu")
    tab = pd.DataFrame({
        "desfecho": desfecho, "termo": resultado.fe_params.index, "coef": resultado.fe_params.values,
        "erro_padrao": resultado.bse_fe.values, "p": resultado.pvalues[resultado.fe_params.index].values,
        "efeitos_aleatorios": tipo,
    })
    return tab


def efeito_tipo_de_pedido(df: pd.DataFrame) -> pd.DataFrame:
    """H5: pedidos que tensionam produzem mais regressões e mais violações novas?

    Regressão: GLMM binomial com `tensiona` (modo incremental e regenerado, com ajuste por modo e passo).
    Violações novas: mudança de arch_violations em relação ao passo anterior, modelo misto.
    """
    glmm = glmm_regressao(df, "y ~ inc + step + tensiona")
    glmm = glmm[glmm["termo"] == "tensiona"].assign(desfecho="regressao (odds ratio)")

    d = df[df["status"] == "ok"].sort_values(["chain_id", "mode", "step"]).copy()
    d["novas"] = d.groupby(["chain_id", "mode"])["arch_violations"].diff()
    d = d[(d["step"] >= 1) & d["novas"].notna()].copy()
    d["novas"] = d["novas"].astype(float)
    d["tensiona"] = (d["request_type"] == "tensiona").astype(int)
    d["inc"] = (d["mode"] == "incremental").astype(int)
    d["chain_id"] = d["chain_id"].astype(int)
    d["step"] = d["step"].astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = smf.mixedlm("novas ~ inc + step + tensiona", d, groups=d["chain_id"]).fit(reml=True)
    linha = pd.DataFrame([{
        "termo": "tensiona", "coef": r.fe_params["tensiona"], "erro_padrao": r.bse_fe["tensiona"],
        "p": r.pvalues["tensiona"], "desfecho": "violacoes novas por passo (diferenca media)",
    }])
    return pd.concat([glmm[["desfecho", "termo", "coef", "erro_padrao", "odds_ratio", "ic95_inf", "ic95_sup", "p"]], linha], ignore_index=True)


def cliffs_delta(x, y) -> float:
    """Delta de Cliff de x contra y: P(x > y) − P(x < y), em [−1, 1]."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    maior = (x[:, None] > y[None, :]).sum()
    menor = (x[:, None] < y[None, :]).sum()
    return float((maior - menor) / (len(x) * len(y)))


def taxa_de_regressao(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df["step"] >= 1) & (df["status"] == "ok")].copy()
    d["taxa"] = d["reg_failed"].astype(float) / d["reg_total"].astype(float)
    return d[["chain_id", "mode", "step", "taxa"]]


def diferenca_pareada(df: pd.DataFrame, desfecho: str = "taxa") -> pd.DataFrame:
    """Incremental − regenerado no mesmo passo, pareando por chain_id.

    Wilcoxon de postos sinalizados por passo e delta de Cliff. Passos em que
    todas as diferenças são zero devolvem p = 1 (nada a testar).
    """
    if desfecho == "taxa":
        base = taxa_de_regressao(df)
    else:
        base = df[(df["step"] >= 1) & (df["status"] == "ok")][["chain_id", "mode", "step", desfecho]].rename(columns={desfecho: "taxa"})
        base["taxa"] = base["taxa"].astype(float)
    larga = base.pivot_table(index=["chain_id", "step"], columns="mode", values="taxa").dropna().reset_index()
    linhas = []
    for passo, g in larga.groupby("step"):
        dif = g["incremental"] - g["regenerado"]
        if len(g) >= 2 and (dif != 0).any():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                p = float(stats.wilcoxon(g["incremental"], g["regenerado"], zero_method="wilcox").pvalue)
        else:
            p = 1.0
        linhas.append({
            "passo": int(passo), "pares": len(g), "dif_media": float(dif.mean()),
            "dif_mediana": float(dif.median()), "wilcoxon_p": p,
            "cliffs_delta": cliffs_delta(g["incremental"], g["regenerado"]),
        })
    return pd.DataFrame(linhas)


def variancia_entre_cadeias(df: pd.DataFrame, desfecho: str = "arch_violations") -> pd.DataFrame:
    """H3: variância do desfecho entre cadeias, por passo e modo, e tendência com o passo."""
    d = df[df["status"] == "ok"].copy()
    d[desfecho] = d[desfecho].astype(float)
    v = d.groupby(["mode", "step"])[desfecho].agg(["var", "count"]).reset_index().rename(columns={"var": "variancia", "count": "cadeias"})
    tendencias = []
    for modo, g in v.dropna().groupby("mode"):
        if len(g) >= 3 and g["variancia"].nunique() > 1:
            rho, p = stats.spearmanr(g["step"], g["variancia"])
        else:
            rho, p = np.nan, np.nan
        tendencias.append({"mode": modo, "spearman_rho": float(rho), "p": float(p)})
    v.attrs["tendencia"] = pd.DataFrame(tendencias)
    return v


def holm(tabela: pd.DataFrame, coluna_p: str = "p", alfa: float = 0.05) -> pd.DataFrame:
    """Acrescenta p ajustado de Holm e a decisão (rejeita H0?) a uma tabela de testes."""
    t = tabela.copy()
    p = t[coluna_p].to_numpy(dtype=float)
    ok = np.isfinite(p)
    ajustado = np.full(len(p), np.nan)
    rejeita = np.zeros(len(p), dtype=bool)
    if ok.any():
        r, pa, _, _ = multipletests(p[ok], alpha=alfa, method="holm")
        ajustado[ok] = pa
        rejeita[ok] = r
    t["p_holm"] = ajustado
    t["rejeita_h0"] = rejeita
    return t
