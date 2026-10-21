"""Conjuntos de dados do painel: os CSVs do repositório e quatro derivados.

Cada número da página vem de um destes conjuntos. Os que vêm do repositório são
cópias dos arquivos de `data/` e de `analise/saida/tabelas/`; os derivados são
calculados aqui a partir deles, e `observados` diz a conta de cada linha.
"""
from __future__ import annotations

import pandas as pd
from scipy import stats

from analise.comum import RAIZ
from analise.rq06 import mapear_linguagem, quartis_labels

T = "analise/saida/tabelas"

# id -> (arquivo no repositório, título, o que é). `None` no arquivo: derivado.
FONTES: dict[str, tuple[str | None, str, str]] = {
    "metricas": ("data/processed/metricas.csv", "Métricas por repositório",
                 "Uma linha por repositório, com as métricas DORA e suas variantes."),
    "funil": ("data/processed/funil.csv", "Funil de seleção",
              "Quantos candidatos entram e saem em cada etapa da seleção da amostra."),
    "classes_c1": (f"{T}/classes_dora_c1.csv", "Classes DORA (C1)",
                   "Repositórios por classe DORA na combinação de referência."),
    "rq01_faixas": (f"{T}/rq01_faixas.csv", "Faixas de frequência (RQ 01)",
                    "Repositórios em cada faixa DORA de frequência de release."),
    "rq05_spearman": (f"{T}/rq05_spearman.csv", "Correlação frequência × CFR",
                      "Spearman entre a frequência de release e cada variante de CFR."),
    "rq06_fatores": (f"{T}/rq06_fatores.csv", "Testes de fatores (RQ 06)",
                     "Kruskal-Wallis de cada fator contra cada métrica, com ε² e p ajustado por Holm."),
    "rq07_pares": (f"{T}/rq07_pares.csv", "Pares de combinações (RQ 07)",
                   "Percentual que mudou de classe e kappa ponderado de cada par."),
    "rq07_contagem": (f"{T}/rq07_classes_por_combinacao.csv", "Classes por combinação (RQ 07)",
                      "Repositórios por classe DORA em C1, C2 e C3."),
    "rq07_mudanca": (f"{T}/rq07_mudanca_por_metrica.csv", "Mudança de nota por métrica (RQ 07)",
                     "Percentual de repositórios cuja nota de cada métrica muda entre dois pares."),
    "rq07_transicoes": (f"{T}/rq07_transicoes.csv", "Transições de classe (RQ 07)",
                        "Quantos repositórios vão de cada classe a cada classe, por par."),
    "rq08b_resumo": (f"{T}/rq08b_resumo.csv", "Tendências por métrica (RQ 08b)",
                     "Repositórios testados e direção da tendência, com e sem Holm."),
    "rq08b_serie": (f"{T}/rq08b_serie_amostra.csv", "Série mensal da amostra (RQ 08b)",
                    "Mediana e IQR mensais entre repositórios, por métrica."),
    "rq08b_freq_tri": (f"{T}/rq08b_frequencia_trimestral.csv", "Frequência por trimestre (RQ 08b)",
                       "Mediana de releases por semana em cada trimestre."),
    "rq08b_lt_tri": (f"{T}/rq08b_lead_time_trimestral.csv", "Lead time por trimestre (RQ 08b)",
                     "Mediana do lead time (a) por trimestre de publicação."),
    "rq08b_mk": (f"{T}/rq08b_amostra_mk.csv", "Mann-Kendall da amostra (RQ 08b)",
                 "Teste de tendência sobre a mediana mensal da amostra."),
    "kappa": ("data/conferencia/kappa.csv", "Concordância entre avaliadores",
              "Kappa de Fleiss dos 3 avaliadores em cada dimensão da conferência manual."),
    "medianas": (None, "Medianas e quartis",
                 "Mediana, quartis, média e p90 de cada métrica, calculados de metricas.csv."),
    "observados": (None, "Números observados",
                   "Contagens e frações usadas nos vereditos; cada linha diz a conta."),
    "rq06_grupos": (None, "Medianas por grupo (RQ 06)",
                    "Mediana de frequência, lead time e CFR (b) por linguagem e por quartil de idade."),
    "heuristica_f1": (None, "F1 da heurística corretiva",
                      "Precisão, recall e F1 das versões v1 a v5, transcritos de docs/metodologia_b.md."),
}
DERIVADOS = [i for i, (arq, _, _) in FONTES.items() if arq is None]

# docs/metodologia_b.md, coluna "decidíveis" (240 releases avaliadas)
F1_HEURISTICA = [("v1", 0.604, 0.443, 0.949), ("v2", 0.535, 0.519, 0.551), ("v3", 0.605, 0.487, 0.796),
                 ("v4", 0.607, 0.442, 0.969), ("v5", 0.638, 0.475, 0.969)]

METRICAS_MEDIANAS = [
    "freq_release", "freq_release_pre", "freq_tag", "lt_release_h", "lt_commit_h", "lt_commit_sem_bots_h",
    "cfr_a", "cfr_a_bruto", "cfr_a_sem_flaky", "pct_falhas_flaky", "cfr_b", "cfr_c",
    "recuperacao_h", "recuperacao_sem_flaky_h", "rework_rate", "rework_rate_7d",
]
CASAS = 6  # arredondamento: o arquivo gerado não pode variar com a versão do scipy


def medianas(m: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for c in METRICAS_MEDIANAS:
        s = m[c].dropna()
        linhas.append({"metrica": c, "n": len(s), "mediana": s.median(), "q1": s.quantile(0.25),
                       "q3": s.quantile(0.75), "media": s.mean(), "p90": s.quantile(0.90)})
    return pd.DataFrame(linhas).round(CASAS)


def observados(m: pd.DataFrame, ep: pd.DataFrame, t6: pd.DataFrame, c7: pd.DataFrame) -> pd.DataFrame:
    """Um número por linha, com a conta dita em `descricao`."""
    linhas: list[dict] = []

    def add(i: str, valor: float, desc: str) -> None:
        linhas.append({"id": i, "valor": float(valor), "descricao": desc})

    r = m["recuperacao_h"].dropna()
    censurado = ep["censurado"].astype(bool)
    so_flaky = ep["so_flaky"].astype(bool)
    mudou = ((c7["nota_C1"] != c7["nota_C2"]) | (c7["nota_C1"] != c7["nota_C3"])
             | (c7["nota_C2"] != c7["nota_C3"]))

    add("n_repos", len(m), "linhas de metricas.csv")
    add("rq01_n_elite", (m["freq_release"] >= 7).sum(), "repositórios com freq_release >= 7 por semana")
    add("rq01_pct_tag_ge_release", (m["freq_tag"] >= m["freq_release"]).mean(), "fração com freq_tag >= freq_release")
    add("rq02_mediana_dias", m["lt_release_h"].median() / 24, "mediana de lt_release_h dividida por 24")
    add("rq02_pct_1a7d", ((m["lt_release_h"] >= 24) & (m["lt_release_h"] < 168)).mean(),
        "fração com lt_release_h entre 1 e 7 dias")
    add("rq02_pct_a_maior_b", (m["lt_release_h"] > m["lt_commit_h"]).mean(), "fração com lt_release_h > lt_commit_h")
    add("rq02_dif_pct", 1 - m["lt_commit_h"].median() / m["lt_release_h"].median(), "1 - mediana(b) / mediana(a)")
    add("rq03a_pct_10a25", ((m["cfr_a"] >= .10) & (m["cfr_a"] <= .25)).mean(), "fração com cfr_a entre 10% e 25%")
    add("rq03a_pct_abaixo10", (m["cfr_a"] < .10).mean(), "fração com cfr_a abaixo de 10%")
    add("rq03a_queda_flaky_pp", (m["cfr_a_bruto"].median() - m["cfr_a_sem_flaky"].median()) * 100,
        "mediana do bruto menos a do sem flaky, em p.p.")
    add("rq03b_pct_abaixo30", (m["cfr_b"] < .30).mean(), "fração com cfr_b abaixo de 30%")
    add("rq04_n_repos", len(r), "repositórios com recuperacao_h")
    add("rq04_n_eps", len(ep), "linhas de episodios.csv")
    add("rq04_eps_censurados", censurado.sum(), "episódios censurados")
    add("rq04_pct_eps_censurados", censurado.mean(), "episódios censurados / total")
    add("rq04_eps_so_flaky", so_flaky.sum(), "episódios só de flaky")
    add("rq04_repos_com_censura", (m["pct_censurados"] > 0).sum(), "repositórios com pct_censurados > 0")
    add("rq04_repos_acima_1dia", (r > 24).sum(), "repositórios com recuperacao_h > 24")
    add("rq04_repos_acima_1sem", (r >= 168).sum(), "repositórios com recuperacao_h >= 168")
    add("rq04_n_high", ((r >= 1) & (r < 24)).sum(), "repositórios com recuperacao_h entre 1 h e 24 h")
    add("rq04_pct_high", ((r >= 1) & (r < 24)).mean(), "fração acima, entre os que têm recuperacao_h")
    add("rq04_sem_recuperacao", len(m) - len(r), "repositórios sem episódio de falha")
    add("rq06_n_testes", len(t6), "linhas de rq06_fatores.csv")
    add("rq06_eps_baixo", (t6["epsilon2"] < .06).sum(), "testes com epsilon2 < 0,06")
    add("rq06_sig_holm", (t6["p_ajustado"] < .05).sum(), "testes com p ajustado < 0,05")
    add("rq07_n_mudou_algum", mudou.sum(), "repositórios que mudam em pelo menos um par")
    add("rq07_pct_mudou_algum", mudou.mean(), "fração acima")
    add("rq08a_pct_rework_1", (m["rework_rate"] == 1).mean(), "fração com rework_rate = 1")
    add("rq08a_n_rework_1", (m["rework_rate"] == 1).sum(), "repositórios com rework_rate = 1")
    add("rq08a_rho_cfr_b", stats.spearmanr(m["rework_rate"], m["cfr_b"], nan_policy="omit").statistic,
        "Spearman entre rework_rate e cfr_b")
    add("rq08a_pct_maior_cfr_b", (m["rework_rate"] > m["cfr_b"]).mean(), "fração com rework_rate > cfr_b")
    add("rq08a_dif_pp", (m["rework_rate"].median() - m["cfr_b"].median()) * 100,
        "mediana de rework_rate menos mediana de cfr_b, em p.p.")
    return pd.DataFrame(linhas).round(CASAS)


def grupos_rq06(m: pd.DataFrame, repos: pd.DataFrame) -> pd.DataFrame:
    """Medianas por linguagem e por quartil de idade, com os mesmos grupos da RQ 06."""
    d = m.merge(repos[["repo", "linguagem", "idade_anos"]], on="repo")
    d["linguagem_top"] = mapear_linguagem(d["linguagem"], 7)
    d["idade_q"] = quartis_labels(d["idade_anos"])
    cols = {"n": ("repo", "size"), "freq_release": ("freq_release", "median"),
            "lt_commit_h": ("lt_commit_h", "median"), "cfr_b": ("cfr_b", "median")}
    lg = d.groupby("linguagem_top", observed=True).agg(**cols).reset_index()
    lg.insert(0, "fator", "linguagem")
    lg = lg.rename(columns={"linguagem_top": "grupo"})
    idade = d.groupby("idade_q", observed=True).agg(
        **cols, idade_min=("idade_anos", "min"), idade_max=("idade_anos", "max")).reset_index()
    idade.insert(0, "fator", "idade")
    idade = idade.rename(columns={"idade_q": "grupo"})
    colunas = ["fator", "grupo", "n", "freq_release", "lt_commit_h", "cfr_b", "idade_min", "idade_max"]
    return pd.concat([lg, idade], ignore_index=True)[colunas].round(CASAS)


def heuristica_f1() -> pd.DataFrame:
    return pd.DataFrame(F1_HEURISTICA, columns=["variante", "f1", "precisao", "recall"])


def ler(caminho: str) -> pd.DataFrame:
    return pd.read_csv(RAIZ / caminho)


def derivados() -> dict[str, pd.DataFrame]:
    m = ler("data/processed/metricas.csv")
    return {
        "medianas": medianas(m),
        "observados": observados(m, ler("data/processed/episodios.csv"), ler(f"{T}/rq06_fatores.csv"),
                                 ler(f"{T}/rq07_classes.csv")),
        "rq06_grupos": grupos_rq06(m, ler("data/processed/repos.csv")),
        "heuristica_f1": heuristica_f1(),
    }
