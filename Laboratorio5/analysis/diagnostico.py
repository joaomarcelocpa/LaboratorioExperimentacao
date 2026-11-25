"""Diagnóstico dos modelos (issue #124): convergência, singularidade, resíduos e plano B.

Cada verificação vira uma linha com o valor observado, se passou e o que
fazer quando não passa. O relatório de análise cita esta tabela em vez de
afirmar que "os modelos estão bem".
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

from analysis import models

LIMITE_SOBREDISPERSAO = 1.5
LIMITE_SD_SINGULAR = 0.05


def _linha(modelo, verificacao, valor, ok, acao="") -> dict:
    return {"modelo": modelo, "verificacao": verificacao, "valor": valor, "ok": bool(ok), "se_falhar": acao}


def _sobredispersao(df: pd.DataFrame) -> float:
    """Pearson χ²/gl de um GLM binomial agregado por passo (sem efeito de cadeia)."""
    d = models._passos_validos(df)
    d["passaram"] = d["reg_total"] - d["reg_failed"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = smf.glm("reg_failed + passaram ~ inc * step", d, family=sm.families.Binomial()).fit()
    return float(r.pearson_chi2 / r.df_resid) if r.df_resid > 0 else float("nan")


def diagnosticar_glmm(df: pd.DataFrame, glmm: pd.DataFrame, gee: pd.DataFrame, fonte: str) -> list[dict]:
    linhas = [_linha("GLMM regressão", "modelo usado como principal", fonte, fonte == "GLMM",
                     "GLMM não estimável: GEE vira o principal (plano B) e o fato vai para as ameaças")]
    d = models._passos_validos(df)
    for modo, g in d.groupby("mode"):
        n = int(g["reg_failed"].sum())
        linhas.append(_linha("GLMM regressão", f"testes que falharam ({modo})", n, n > 0,
                             "sem eventos num modo há separação: reportar só a descritiva e o log-rank"))
    if "sd_cadeia_logit" in glmm:
        sd = float(glmm["sd_cadeia_logit"].iloc[0])
        linhas.append(_linha("GLMM regressão", "dp do intercepto da cadeia (logit)", sd, sd > LIMITE_SD_SINGULAR,
                             "efeito de cadeia ~0 (ajuste singular): o GEE e o GLM sem efeito aleatório bastam"))
    od = _sobredispersao(df)
    linhas.append(_linha("GLMM regressão", "sobredispersão (Pearson χ²/gl, GLM sem cadeia)", od, od <= LIMITE_SOBREDISPERSAO,
                         "testes falham em bloco: preferir os erros robustos do GEE e declarar na ameaça"))
    a = glmm.set_index("termo").loc["inc:step"]
    b = gee.set_index("termo").loc["inc:step"]
    mesmo_sinal = np.sign(a["coef"]) == np.sign(b["coef"])
    mesma_decisao = (a["p"] < 0.05) == (b["p"] < 0.05)
    linhas.append(_linha("GLMM regressão", "GLMM e GEE concordam no sinal de modo × passo", f"{a['coef']:.3f} / {b['coef']:.3f}", mesmo_sinal,
                         "vale o mais conservador; divergência vai para as ameaças"))
    linhas.append(_linha("GLMM regressão", "GLMM e GEE concordam na significância (α = 0,05)", f"p = {a['p']:.4f} / {b['p']:.4f}", mesma_decisao,
                         "vale o mais conservador; divergência vai para as ameaças"))
    return linhas


def diagnosticar_crescimento(df: pd.DataFrame, desfecho: str) -> list[dict]:
    nome = f"crescimento {desfecho}"
    try:
        r, tipo, _ = models.ajustar_crescimento(df, desfecho)
    except RuntimeError as e:
        return [_linha(nome, "ajuste", str(e), False, "reportar só a descritiva e a diferença pareada desse desfecho")]
    linhas = [
        _linha(nome, "efeitos aleatórios usados", tipo, tipo.startswith("intercepto+inclinação"),
               "inclinação por cadeia não estimável: modelo só com intercepto (registrado na tabela)"),
        _linha(nome, "otimizador convergiu", bool(getattr(r, "converged", True)), getattr(r, "converged", True),
               "nenhum otimizador (lbfgs, powell, nm, bfgs) convergiu: tratar o resultado como exploratório"),
    ]
    var_int = float(np.diag(np.atleast_2d(r.cov_re))[0])
    linhas.append(_linha(nome, "variância do intercepto da cadeia", var_int, var_int > 1e-6,
                         "ajuste singular: o efeito de cadeia não aparece nos dados; resultado ≈ OLS"))
    res = np.asarray(r.resid, dtype=float)
    amostra = res if len(res) <= 5000 else np.random.default_rng(42).choice(res, 5000, replace=False)
    p_norm = float(stats.shapiro(amostra).pvalue) if len(amostra) >= 3 and np.std(amostra) > 0 else float("nan")
    linhas.append(_linha(nome, "normalidade dos resíduos (Shapiro p)", p_norm, not (p_norm < 0.01),
                         "contagens assimétricas: conferir com a diferença pareada (não paramétrica) e com log(1+y)"))
    linhas.append(_linha(nome, "assimetria dos resíduos", float(stats.skew(res)), abs(stats.skew(res)) < 1,
                         "contagens assimétricas: conferir com a diferença pareada (não paramétrica) e com log(1+y)"))
    return linhas


def diagnosticar(df: pd.DataFrame, glmm: pd.DataFrame, gee: pd.DataFrame, fonte: str,
                 desfechos=("arch_violations", "files_touched", "dup_pct")) -> pd.DataFrame:
    linhas = diagnosticar_glmm(df, glmm, gee, fonte)
    for d in desfechos:
        linhas += diagnosticar_crescimento(df, d)
    return pd.DataFrame(linhas)
