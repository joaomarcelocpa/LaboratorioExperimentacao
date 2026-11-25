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


def ordem_das_cadeias(df: pd.DataFrame) -> pd.Series:
    """Ordem de cada (chain_id, mode), deduzida do pedido do passo 1.

    O esquema congelado não tem coluna de ordem; o protocolo (seção 3) define
    a Ordem A começando por P1 e a Ordem B começando por P2.
    """
    p1 = df[df["step"] == 1].set_index(["chain_id", "mode"])["request_id"]
    return p1.map({"P1": "A", "P2": "B"}).rename("ordem")


def _passos_validos(df: pd.DataFrame) -> pd.DataFrame:
    """Passos 1..10 com execução concluída (status ok), com as covariáveis codificadas."""
    d = df[(df["step"] >= 1) & (df["status"] == "ok")].copy()
    for c in ("reg_total", "reg_failed", "step", "chain_id"):
        d[c] = d[c].astype(int)
    d["inc"] = (d["mode"] == "incremental").astype(int)
    d["tensiona"] = (d["request_type"] == "tensiona").astype(int)
    d["rodou_testes"] = d["agent_ran_tests"].astype(float).fillna(0).astype(int)
    ordem = ordem_das_cadeias(df)
    d["ordem_b"] = [int(ordem.get((c, m)) == "B") for c, m in zip(d["chain_id"], d["mode"])]
    return d


def expandir_testes(d: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por teste de regressão executado (y = 1 se falhou)."""
    repete = d["reg_total"].to_numpy()
    base = d.loc[d.index.repeat(repete), ["chain_id", "mode", "inc", "step", "tensiona", "rodou_testes", "ordem_b"]].reset_index(drop=True)
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


def glmm_regressao(df: pd.DataFrame, formula_fixa: str = "y ~ inc * step", _dados: pd.DataFrame | None = None) -> pd.DataFrame:
    """GLMM binomial com intercepto aleatório por cadeia (Bayes variacional).

    statsmodels não traz GLMM por máxima verossimilhança; BinomialBayesMixedGLM
    ajusta o mesmo modelo por aproximação variacional. Os "IC 95%" são
    intervalos de credibilidade aproximados (média ± 1,96 dp a posteriori) e
    tendem a ser estreitos; por isso `glmm_sensibilidade` confere com GEE.
    """
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    t = expandir_testes(_dados if _dados is not None else _passos_validos(df))
    if t["y"].nunique() < 2:
        raise ValueError("sem variação no desfecho (nenhum teste falhou, ou todos falharam): GLMM não estimável")
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


FORMULA_COVARIAVEIS = "y ~ inc * step + rodou_testes + ordem_b"


def glmm_covariaveis(df: pd.DataFrame) -> pd.DataFrame:
    """GLMM de H1/H4 ajustado por `agent_ran_tests` e pela ordem dos pedidos (sensibilidade).

    Fica fora do modelo principal porque `agent_ran_tests` é decidido pelo
    agente durante o passo (pós-tratamento): ajustar por ele pode absorver
    parte do efeito do modo. Se o termo inc:step muda pouco entre os dois
    modelos, o resultado não depende dessas covariáveis. Termo que não varia
    nos dados (ex.: uma ordem só) sai da fórmula.
    """
    d = _passos_validos(df)
    formula = FORMULA_COVARIAVEIS
    for termo in ("rodou_testes", "ordem_b"):
        if d[termo].nunique() < 2:
            formula = formula.replace(f" + {termo}", "")
    return glmm_regressao(df, formula, _dados=d).assign(formula=formula)


def ajustar_crescimento(df: pd.DataFrame, desfecho: str):
    """Ajusta o modelo misto de `curva_de_crescimento`. Devolve (resultado, rótulo dos efeitos aleatórios, dados)."""
    d = df[df["status"] == "ok"].copy()
    d = d[d[desfecho].notna()]
    d[desfecho] = d[desfecho].astype(float)
    d["step"] = d["step"].astype(int)
    d["chain_id"] = d["chain_id"].astype(int)
    d["inc"] = (d["mode"] == "incremental").astype(int)
    formula = f"{desfecho} ~ inc * step"
    # Ordem de preferência: inclinação aleatória antes de só intercepto; em cada
    # uma, tenta otimizadores até um convergir. Sem convergência em nenhum, usa o
    # primeiro ajuste com erros finitos e o diagnóstico acusa.
    reserva = None
    for re_formula, rotulo in (("~step", "intercepto+inclinação"), ("~1", "intercepto")):
        for metodo in ("lbfgs", "powell", "nm", "bfgs"):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = smf.mixedlm(formula, d, groups=d["chain_id"], re_formula=re_formula)
                    r = m.fit(method=metodo, reml=True, maxiter=2000)
            except Exception:
                continue
            if not np.isfinite(r.bse_fe).all():
                continue
            if getattr(r, "converged", True):
                return r, f"{rotulo} ({metodo})", d
            reserva = reserva or (r, f"{rotulo} ({metodo}, sem convergência)", d)
    if reserva:
        return reserva
    raise RuntimeError(f"curva de crescimento de {desfecho} não convergiu")


def curva_de_crescimento(df: pd.DataFrame, desfecho: str) -> pd.DataFrame:
    """Modelo misto: desfecho ~ modo × passo, intercepto e inclinação aleatórios por cadeia.

    Se a inclinação aleatória não converge (poucas cadeias), cai para só
    intercepto aleatório e marca `efeitos_aleatorios` na saída.
    """
    resultado, tipo, _ = ajustar_crescimento(df, desfecho)
    return pd.DataFrame({
        "desfecho": desfecho, "termo": resultado.fe_params.index, "coef": resultado.fe_params.values,
        "erro_padrao": resultado.bse_fe.values, "p": resultado.pvalues[resultado.fe_params.index].values,
        "ic95_inf": resultado.fe_params.values - 1.96 * resultado.bse_fe.values,
        "ic95_sup": resultado.fe_params.values + 1.96 * resultado.bse_fe.values,
        "efeitos_aleatorios": tipo,
    })


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


def _bootstrap_pares(inc, reg, n_boot: int = 2000, seed: int = 42) -> tuple[float, float, float, float]:
    """IC 95% percentil, reamostrando pares: (cliff_inf, cliff_sup, dif_mediana_inf, dif_mediana_sup)."""
    inc = np.asarray(inc, dtype=float)
    reg = np.asarray(reg, dtype=float)
    if len(inc) < 2:
        return (np.nan,) * 4
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(inc), size=(n_boot, len(inc)))
    cliffs = np.array([cliffs_delta(inc[i], reg[i]) for i in idx])
    medianas = np.median(inc[idx] - reg[idx], axis=1)
    return (*np.percentile(cliffs, [2.5, 97.5]), *np.percentile(medianas, [2.5, 97.5]))


def diferenca_pareada(df: pd.DataFrame, desfecho: str = "taxa") -> pd.DataFrame:
    """Incremental − regenerado no mesmo passo, pareando por chain_id.

    Pareamento: a cadeia i incremental com a cadeia i regenerada, que recebem
    os mesmos pedidos na mesma ordem e terminam no mesmo passo. Wilcoxon de
    postos sinalizados por passo e delta de Cliff, com IC 95% por bootstrap de
    pares. Passos em que todas as diferenças são zero devolvem p = 1.
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
        c_inf, c_sup, m_inf, m_sup = _bootstrap_pares(g["incremental"], g["regenerado"])
        linhas.append({
            "passo": int(passo), "pares": len(g), "dif_media": float(dif.mean()),
            "dif_mediana": float(dif.median()), "dif_mediana_ic95_inf": m_inf, "dif_mediana_ic95_sup": m_sup,
            "wilcoxon_p": p,
            "cliffs_delta": cliffs_delta(g["incremental"], g["regenerado"]),
            "cliffs_ic95_inf": c_inf, "cliffs_ic95_sup": c_sup,
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
