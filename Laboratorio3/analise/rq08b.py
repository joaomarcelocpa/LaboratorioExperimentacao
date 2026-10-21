"""RQ 08b: as métricas DORA melhoraram ou pioraram ao longo da janela?

Métrica: proporção de repositórios com tendência significativa de melhora, de
piora e sem tendência, por métrica.

Por que mensal e não só por trimestre: com 4 pontos o teste de Mann-Kendall não
chega a p < 0,05 nem numa série perfeitamente crescente (o menor p possível com
n = 4 é ≈ 0,08), então testar por trimestre daria sempre "nenhum repositório
com tendência", por limitação do teste e não dos dados. Por isso:

1. **Métricas de CI, por mês (12 pontos), é onde se testa.** CFR de CI oficial
   (`cfr_a`) e mediana do tempo de recuperação (`recuperacao_h`), de
   `metricas_mensais.csv`. Mês sem valor (menos de 5 runs válidos) fica de fora,
   e o repositório com menos de 8 meses válidos não entra no teste.
2. **Frequência e lead time, por trimestre (4 pontos): só descritivo**, a
   mediana por trimestre da amostra, sem teste.
3. **Teste por repositório:** `pymannkendall.original_test` com α = 0,05, com
   `hamed_rao_modification_test` ao lado para checar quando há autocorrelação, e
   a inclinação de Sen como tamanho de efeito (p.p. por mês no CFR, horas por mês
   na recuperação).
4. **Direção:** para as duas métricas, queda é melhora.
5. **Muitos testes:** um teste por repositório gera centenas de p-valores, então
   as proporções saem com e sem a correção de Holm, uma família por métrica.
6. **Visão da amostra:** a série mensal da mediana entre repositórios, com a
   faixa do IQR, e o Mann-Kendall sobre ela.
"""
from __future__ import annotations

import math
import warnings
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pymannkendall as mk
from statsmodels.stats.multitest import multipletests

from analise import comum
from metricas.frequencia import frequencia
from metricas.lead_time import lead_time_por_release
from pipeline.config import carregar_config

ALFA = 0.05
MIN_MESES = 8

# inclinação de Sen: cfr_a sai em proporção/mês, e vira pontos percentuais/mês
ESCALA = {"cfr_a": 100.0, "recuperacao_h": 1.0}
UNIDADE = {"cfr_a": "p.p./mês", "recuperacao_h": "h/mês"}
ROTULO = {"cfr_a": "CFR de CI (a)", "recuperacao_h": "Tempo de recuperação (h)"}
METRICAS = list(ESCALA)


# --- um repositório -----------------------------------------------------------------

def _autocorrelacao_lag1(x: np.ndarray, inclinacao: float, intercepto: float) -> bool:
    """Os resíduos da reta de Sen têm autocorrelação de lag 1 acima de 2/√n?"""
    t = np.arange(len(x))
    e = x - (intercepto + inclinacao * t)
    e = e - e.mean()
    denominador = float((e ** 2).sum())
    if denominador == 0.0:
        return False
    r1 = float((e[:-1] * e[1:]).sum()) / denominador
    return bool(abs(r1) > 2 / math.sqrt(len(x)))


def teste_tendencia(serie: pd.Series, metrica: str) -> dict:
    """Mann-Kendall de uma série mensal (índice = mês `AAAA-MM`).

    A série é ordenada por mês e os meses sem valor saem dela (não viram zero).
    Com menos de `MIN_MESES` meses válidos o repositório não é testado.
    Direção: queda é melhora, tanto no CFR quanto no tempo de recuperação.
    """
    valores = serie.sort_index().dropna()
    n = len(valores)
    resultado = {"n_meses": n, "testado": False, "p": math.nan, "p_hamed_rao": math.nan,
                 "inclinacao": math.nan, "tau": math.nan, "autocorrelacao": False,
                 "direcao": "não testado"}
    if n < MIN_MESES:
        return resultado

    x = valores.to_numpy(dtype=float)
    r = mk.original_test(x, alpha=ALFA)
    p = float(r.p)
    try:
        # com a variância corrigida negativa o pymannkendall devolve NaN e avisa
        # (RuntimeWarning); o NaN já diz que a checagem não se aplica
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            p_hr = float(mk.hamed_rao_modification_test(x, alpha=ALFA).p)
    except Exception:  # noqa: BLE001 — séries degeneradas: a checagem fica vazia
        p_hr = math.nan

    # A direção vem do sinal do teste (a estatística S), e não da inclinação de
    # Sen: com muitos empates a mediana das inclinações pode ser 0 num repositório
    # cuja alta é significativa. A inclinação fica como tamanho de efeito.
    direcao = {"decreasing": "melhora", "increasing": "piora"}.get(r.trend, "sem tendência")
    resultado.update({
        "testado": True,
        "p": p,
        "p_hamed_rao": p_hr,
        "inclinacao": float(r.slope) * ESCALA[metrica],
        "tau": float(r.Tau),
        "autocorrelacao": _autocorrelacao_lag1(x, float(r.slope), float(r.intercept)),
        "direcao": direcao,
    })
    return resultado


def aplicar_holm(p: pd.Series) -> pd.Series:
    """Correção de Holm sobre os p-valores presentes; NaN continua NaN."""
    saida = pd.Series(np.nan, index=p.index, dtype=float)
    validos = p.dropna()
    if validos.empty:
        return saida
    ajustado = multipletests(validos.to_numpy(), alpha=ALFA, method="holm")[1]
    saida.loc[validos.index] = ajustado
    return saida


# --- todos os repositórios ----------------------------------------------------------------

def tendencias_por_repo(mensais: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """Uma linha por repositório, com o teste, o p ajustado por Holm e as direções."""
    linhas = []
    for repo, grupo in mensais.groupby("repo", sort=True):
        r = teste_tendencia(grupo.set_index("mes")[metrica], metrica)
        r["difere_hamed_rao"] = bool(
            r["autocorrelacao"] and not math.isnan(r["p_hamed_rao"])
            and ((r["p"] < ALFA) != (r["p_hamed_rao"] < ALFA)))
        linhas.append({"repo": repo, **r})
    t = pd.DataFrame(linhas)
    t["p_holm"] = aplicar_holm(t["p"])
    # a direção por Holm: a mesma, só que exigindo o p ajustado abaixo de α
    t["direcao_holm"] = [
        d if (d == "não testado" or (ph < ALFA)) else "sem tendência"
        for d, ph in zip(t["direcao"], t["p_holm"])
    ]
    colunas = ["repo", "n_meses", "testado", "p", "p_holm", "p_hamed_rao", "autocorrelacao",
               "difere_hamed_rao", "inclinacao", "tau", "direcao", "direcao_holm"]
    return t[colunas]


def resumo(t: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """Proporção de melhora, piora e sem tendência, com e sem Holm.

    As proporções têm como denominador os repositórios TESTADOS; quem ficou fora
    por ter poucos meses válidos aparece em `excluidos`.
    """
    testados = t[t["testado"].astype(bool)]
    n = len(testados)
    linha = {"repos": len(t), "testados": n, "excluidos": len(t) - n}
    for sufixo, coluna in (("", "direcao"), ("_holm", "direcao_holm")):
        contagem = testados[coluna].value_counts()
        for nome, rotulo in (("melhora", "melhora"), ("piora", "piora"),
                             ("sem_tendencia", "sem tendência")):
            k = int(contagem.get(rotulo, 0))
            linha[f"{nome}{sufixo}"] = k
            linha[f"pct_{nome}{sufixo}"] = k / n if n else math.nan
    if "difere_hamed_rao" in t.columns:
        linha["difere_hamed_rao"] = int(testados["difere_hamed_rao"].sum())
    return pd.DataFrame([linha], index=pd.Index([metrica], name="metrica"))


# --- visão da amostra -----------------------------------------------------------------------

def serie_amostra(mensais: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """Mediana e IQR entre repositórios, mês a mês, com o n de cada mês."""
    g = mensais.groupby("mes")[metrica]
    return pd.DataFrame({
        "n": g.count(),
        "mediana": g.median(),
        "q1": g.quantile(0.25),
        "q3": g.quantile(0.75),
    }).reset_index().sort_values("mes").reset_index(drop=True)


def tendencia_amostra(serie: pd.DataFrame, metrica: str) -> dict:
    """Mann-Kendall sobre a série mensal da mediana da amostra."""
    return teste_tendencia(serie.set_index("mes")["mediana"], metrica)


# --- frequência e lead time por trimestre (descritivo) -----------------------------------------

def _trimestres(inicio: date, fim: date):
    for q in pd.period_range(inicio, fim, freq="Q"):
        yield q, max(inicio, q.start_time.date()), min(fim, q.end_time.date())


def _quartis(valores: pd.Series) -> dict:
    return {"mediana": float(valores.median()), "q1": float(valores.quantile(0.25)),
            "q3": float(valores.quantile(0.75))}


def frequencia_trimestral(releases: pd.DataFrame, inicio: date, fim: date) -> pd.DataFrame:
    """Mediana, entre repositórios, das releases por semana em cada trimestre.

    Mesma definição de `freq_release`: releases na janela, sem pré-release.
    Repositório sem release no trimestre entra com 0.
    """
    estaveis = releases[releases["na_janela"].astype(bool) & ~releases["prerelease"].astype(bool)]
    por_repo = {r: g for r, g in estaveis.groupby("repo")}
    repos = sorted(releases["repo"].unique())
    linhas = []
    for q, ini_q, fim_q in _trimestres(inicio, fim):
        freq = pd.Series({
            r: (frequencia(por_repo[r], ini_q, fim_q) if r in por_repo else 0.0) for r in repos})
        linhas.append({"trimestre": str(q), **_quartis(freq), "n_repos": len(freq)})
    return pd.DataFrame(linhas, columns=["trimestre", "mediana", "q1", "q3", "n_repos"])


def lead_time_trimestral(releases: pd.DataFrame, commits: pd.DataFrame) -> pd.DataFrame:
    """Mediana, entre repositórios, do lead time (a) por trimestre de publicação.

    Primeiro a mediana por repositório e trimestre, depois a mediana entre
    repositórios. Release sem commits ou sem release anterior fica de fora.
    """
    publicada = pd.to_datetime(releases["publicada_em"], utc=True)
    linhas = []
    for repo, rel in releases.groupby("repo"):
        com = commits[commits["repo"] == repo] if not commits.empty else commits
        lt = lead_time_por_release(rel, com).dropna()
        if lt.empty:
            continue
        quando = publicada.loc[rel.index].groupby(rel["tag"].values).first()
        trimestre = quando.reindex(lt.index).dt.tz_localize(None).dt.to_period("Q").astype(str)
        for q, valores in lt.groupby(trimestre):
            linhas.append({"repo": repo, "trimestre": q, "lt": float(valores.median())})
    if not linhas:
        return pd.DataFrame(columns=["trimestre", "mediana_h", "q1_h", "q3_h", "n_repos"])
    por_repo = pd.DataFrame(linhas)
    saida = []
    for q, g in por_repo.groupby("trimestre"):
        d = _quartis(g["lt"])
        saida.append({"trimestre": q, "mediana_h": d["mediana"], "q1_h": d["q1"],
                      "q3_h": d["q3"], "n_repos": len(g)})
    return pd.DataFrame(saida)


# --- entradas e saídas ---------------------------------------------------------------------------

def carregar_releases() -> pd.DataFrame:
    return comum._ler("releases.csv")


def carregar_commits() -> pd.DataFrame:
    """commits.csv.gz (entregue) ou o commits.csv de um checkpoint em andamento."""
    for nome in ("commits.csv.gz", "commits.csv"):
        if (comum.DADOS / nome).exists():
            return comum._ler(nome)
    raise FileNotFoundError(f"{comum.DADOS}/commits.csv.gz não existe: rode `make run` antes")


def janela() -> tuple[date, date]:
    cfg = carregar_config(comum.RAIZ / "config.yaml")
    return cfg.janela_inicio, cfg.janela_fim


def figura_serie(series: dict[str, pd.DataFrame], mks: dict[str, dict]) -> plt.Figure:
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, metrica in zip(eixos, METRICAS):
        s = series[metrica]
        escala = 100.0 if metrica == "cfr_a" else 1.0
        x = range(len(s))
        ax.fill_between(x, s["q1"] * escala, s["q3"] * escala, alpha=0.25, color="#4C72B0",
                        label="IQR entre repositórios")
        ax.plot(x, s["mediana"] * escala, marker="o", color="#4C72B0", label="mediana")
        ax.set_xticks(list(x))
        ax.set_xticklabels(s["mes"], rotation=45, ha="right")
        ax.set_ylabel(ROTULO[metrica] + (" (%)" if metrica == "cfr_a" else ""))
        r = mks[metrica]
        ax.set_title(f"{ROTULO[metrica]}\n"
                     f"Mann-Kendall da mediana: {r['direcao']} (p = {r['p']:.3f})\n"
                     f"repositórios por mês: {int(s['n'].min())} a {int(s['n'].max())}",
                     fontsize=10)
        ax.legend()
    fig.suptitle("RQ 08b · Evolução mensal na amostra")
    fig.tight_layout()
    return fig


def main() -> None:
    mensais = comum.carregar_metricas_mensais()
    ini, fim = janela()

    tendencias, resumos, series, mks = [], [], {}, {}
    for metrica in METRICAS:
        t = tendencias_por_repo(mensais, metrica)
        tendencias.append(t.assign(metrica=metrica))
        resumos.append(resumo(t, metrica))
        series[metrica] = serie_amostra(mensais, metrica)
        mks[metrica] = tendencia_amostra(series[metrica], metrica)

    tend = pd.concat(tendencias, ignore_index=True)
    res = pd.concat(resumos)
    serie_longa = pd.concat([s.assign(metrica=m) for m, s in series.items()], ignore_index=True)
    mk_amostra = pd.DataFrame(
        {m: {k: r[k] for k in ("n_meses", "p", "inclinacao", "tau", "direcao")}
         for m, r in mks.items()}).T.rename_axis("metrica")
    freq = frequencia_trimestral(carregar_releases(), ini, fim)
    lt = lead_time_trimestral(carregar_releases(), carregar_commits())

    print("\n=== RQ 08b · Proporção de repositórios por direção da tendência ===")
    print(res.round(3).T.to_string())
    print("\n=== RQ 08b · Mann-Kendall sobre a mediana da amostra ===")
    print(mk_amostra.to_string())
    print("\n=== Frequência de releases por trimestre (releases/semana) ===")
    print(freq.round(3).to_string(index=False))
    print("\n=== Lead time (a) por trimestre (horas) ===")
    print(lt.round(1).to_string(index=False))

    comum.salvar_tabela(tend.set_index(["metrica", "repo"]), "rq08b_tendencias")
    comum.salvar_tabela(res, "rq08b_resumo")
    comum.salvar_tabela(serie_longa.set_index(["metrica", "mes"]), "rq08b_serie_amostra")
    comum.salvar_tabela(mk_amostra, "rq08b_amostra_mk")
    comum.salvar_tabela(freq.set_index("trimestre"), "rq08b_frequencia_trimestral")
    comum.salvar_tabela(lt.set_index("trimestre"), "rq08b_lead_time_trimestral")
    comum.salvar_figura(figura_serie(series, mks), "rq08b_serie_amostra")


if __name__ == "__main__":  # pragma: no cover
    main()
