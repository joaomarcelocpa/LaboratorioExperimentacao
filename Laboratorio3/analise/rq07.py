"""RQ 07: o quanto a classificação DORA depende da definição operacional.

Análise de sensibilidade: o mesmo repositório é classificado (Elite / High /
Medium / Low) sob três combinações de definições e as classificações são
comparadas par a par.

| Combinação | Unidade de deploy        | Lead time        | CFR              |
|------------|--------------------------|------------------|------------------|
| C1         | release                  | (a) por release  | (a) falha de CI  |
| C2         | release + pré-release    | (b) por commit   | (b) release corretiva |
| C3         | tag                      | (b) por commit   | (a) falha de CI  |

O tempo de recuperação (a quarta métrica da classificação) é o mesmo nas três:
o enunciado só varia unidade de deploy, lead time e CFR. Os cortes e a regra da
mediana são os de `metricas.classificacao`, os mesmos da C1 (`analise.rq03_rq04`),
então só a definição muda, nunca o critério de classificar.

Para cada par: a % de repositórios que mudaram de categoria e o kappa de Cohen
ponderado linear. As categorias são ordenadas, então trocar Elite por High pesa
menos que trocar Elite por Low.
"""
from __future__ import annotations

import itertools
import math
import warnings

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from analise import comum
from analise.rq03_rq04 import ORDEM
from metricas.classificacao import classificar_metrica, classificar_repo

COMBINACOES = {
    "C1": {"freq": "freq_release", "lead_time": "lt_release_h", "cfr": "cfr_a"},
    "C2": {"freq": "freq_release_pre", "lead_time": "lt_commit_h", "cfr": "cfr_b"},
    "C3": {"freq": "freq_tag", "lead_time": "lt_commit_h", "cfr": "cfr_a"},
}
RECUPERACAO = "recuperacao_h"
PARES = [f"{a}x{b}" for a, b in itertools.combinations(COMBINACOES, 2)]
# notas 1-4 em ordem crescente de desempenho, como em metricas.schemas.NOTAS_DORA
NOTAS = [1, 2, 3, 4]


def classificar_combinacao(df: pd.DataFrame, combinacao: dict) -> pd.DataFrame:
    """Notas por métrica e classe de cada repositório sob uma combinação.

    Mesmas colunas de `rq03_rq04.reclassificar_c1`, para que a C1 daqui possa
    ser conferida contra a da RQ 03/04.
    """
    colunas = {**combinacao, "recuperacao": RECUPERACAO}
    saida = pd.DataFrame({"repo": df["repo"].values})
    for metrica, coluna in colunas.items():
        saida[f"nota_{metrica}"] = [classificar_metrica(metrica, v) for v in df[coluna]]
    notas = [f"nota_{m}" for m in colunas]
    classes = [classificar_repo([linha[n] for n in notas]) for _, linha in saida.iterrows()]
    saida["classe_dora"] = pd.Series([c for c, _ in classes], dtype=object)
    saida["classe_dora_nota"] = [n for _, n in classes]
    return saida


def classificar_todas(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por repositório com `classe_Cx` e `nota_Cx` de cada combinação."""
    saida = pd.DataFrame({"repo": df["repo"].values})
    for nome, combinacao in COMBINACOES.items():
        c = classificar_combinacao(df, combinacao)
        saida[f"classe_{nome}"] = c["classe_dora"].values
        saida[f"nota_{nome}"] = c["classe_dora_nota"].values
    return saida


def comparar_par(a: pd.Series, b: pd.Series) -> dict:
    """% que mudou de categoria e kappa ponderado entre duas classificações.

    `a` e `b` são as notas 1-4 de cada repositório. Quem não tem nota num dos
    lados fica fora do par, e `n` diz quantos sobraram.

    As categorias são fixadas em 1-4: sem isso o scikit-learn usa só as que
    aparecem e as trata como igualmente espaçadas, e o kappa muda quando falta
    uma classe no meio. Sem nenhuma variação (todos na mesma classe nos dois
    lados) o kappa não existe, e vira NaN em vez de um aviso.
    """
    pares = pd.DataFrame({"a": a.values, "b": b.values}).dropna()
    n = len(pares)
    if n == 0:
        return {"n": 0, "mudaram": 0, "pct_mudou": math.nan, "subiram": 0,
                "desceram": 0, "kappa": math.nan}
    x, y = pares["a"].astype(int), pares["b"].astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kappa = float(cohen_kappa_score(x, y, weights="linear", labels=NOTAS))
    return {
        "n": n,
        "mudaram": int((x != y).sum()),
        "pct_mudou": float((x != y).mean()),
        "subiram": int((y > x).sum()),
        "desceram": int((y < x).sum()),
        "kappa": kappa,
    }


def leitura_kappa(kappa: float) -> str:
    """Faixas de Landis e Koch (1977), como no enunciado."""
    if kappa is None or math.isnan(kappa):
        return "indefinida"
    for corte, texto in ((0.0, "pobre"), (0.20, "leve"), (0.40, "razoável"),
                         (0.60, "moderada"), (0.80, "substancial")):
        if kappa < corte if corte == 0.0 else kappa <= corte:
            return texto
    return "quase perfeita"


def tabela_pares(todas: pd.DataFrame) -> pd.DataFrame:
    """C1xC2, C1xC3 e C2xC3: n, mudanças, kappa ponderado e a leitura dele."""
    linhas = {}
    for par in PARES:
        a, b = par.split("x")
        r = comparar_par(todas[f"nota_{a}"], todas[f"nota_{b}"])
        r["pct_mudou"] = round(r["pct_mudou"], 4)
        r["kappa"] = round(r["kappa"], 4)
        r["concordancia"] = leitura_kappa(r["kappa"])
        linhas[par] = r
    colunas = ["n", "mudaram", "pct_mudou", "subiram", "desceram", "kappa", "concordancia"]
    return pd.DataFrame.from_dict(linhas, orient="index")[colunas].rename_axis("par")


def mudanca_por_metrica(df: pd.DataFrame) -> pd.DataFrame:
    """Em qual métrica a definição pesa: % de repositórios cuja nota mudou.

    Para cada par, compara a nota que cada combinação dá a cada métrica. Onde as
    duas combinações usam a mesma coluna (ex.: o CFR (a) na C1 e na C3) o
    resultado é 0 por construção.
    """
    linhas = []
    for par in PARES:
        a, b = par.split("x")
        for metrica in ("freq", "lead_time", "cfr"):
            na = pd.Series([classificar_metrica(metrica, v)
                            for v in df[COMBINACOES[a][metrica]]])
            nb = pd.Series([classificar_metrica(metrica, v)
                            for v in df[COMBINACOES[b][metrica]]])
            r = comparar_par(na, nb)
            linhas.append({"par": par, "metrica": metrica, "n": r["n"],
                           "pct_nota_mudou": round(r["pct_mudou"], 4)})
    return pd.DataFrame(linhas)


def contagem_por_combinacao(todas: pd.DataFrame) -> pd.DataFrame:
    """Quantos repositórios cada classe tem em cada combinação."""
    cont = {nome: todas[f"classe_{nome}"].value_counts().reindex(ORDEM, fill_value=0)
            for nome in COMBINACOES}
    return pd.DataFrame(cont).rename_axis("classe")


def matriz_transicao(todas: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """Linhas: classe na combinação `a`. Colunas: classe na `b`."""
    ambos = todas[[f"classe_{a}", f"classe_{b}"]].dropna()
    m = pd.crosstab(ambos[f"classe_{a}"], ambos[f"classe_{b}"])
    return m.reindex(index=ORDEM, columns=ORDEM, fill_value=0)


def transicoes_longas(todas: pd.DataFrame) -> pd.DataFrame:
    """As três matrizes de transição num só arquivo: par, de, para, n."""
    linhas = []
    for par in PARES:
        a, b = par.split("x")
        m = matriz_transicao(todas, a, b)
        for de in ORDEM:
            for para in ORDEM:
                linhas.append({"par": par, "de": de, "para": para, "n": int(m.loc[de, para])})
    return pd.DataFrame(linhas)


def figura_classes(contagem: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    largura = 0.26
    cores = ["#4C72B0", "#DD8452", "#55A868"]
    base = range(len(ORDEM))
    for i, (nome, cor) in enumerate(zip(COMBINACOES, cores)):
        xs = [p + (i - 1) * largura for p in base]
        barras = ax.bar(xs, contagem[nome].values, largura, label=nome, color=cor)
        for barra in barras:
            ax.text(barra.get_x() + barra.get_width() / 2, barra.get_height(),
                    str(int(barra.get_height())), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(base))
    ax.set_xticklabels(ORDEM)
    ax.set_ylabel("repositórios")
    ax.set_title(f"RQ 07 · Classe DORA por combinação (n = {int(contagem['C1'].sum())})")
    ax.legend(title="combinação")
    fig.tight_layout()
    return fig


def main() -> None:
    df = comum.carregar_metricas()
    todas = classificar_todas(df)

    # A C1 daqui precisa ser a mesma classe_dora do metricas.csv.
    if "classe_dora" in df.columns:
        diverge = int((todas["classe_C1"].fillna("-").values
                       != df["classe_dora"].fillna("-").values).sum())
        print(f"C1 difere da classe_dora do metricas.csv em {diverge} repositórios")

    pares = tabela_pares(todas)
    contagem = contagem_por_combinacao(todas)
    por_metrica = mudanca_por_metrica(df)

    print("\n=== RQ 07 · Classe DORA por combinação ===")
    print(contagem.to_string())
    print("\n=== RQ 07 · Pares: % que mudou de categoria e kappa ponderado ===")
    print(pares.to_string())
    print("\n=== RQ 07 · % de notas que mudaram, por métrica ===")
    print(por_metrica.to_string(index=False))

    comum.salvar_tabela(todas.set_index("repo"), "rq07_classes")
    comum.salvar_tabela(pares, "rq07_pares")
    comum.salvar_tabela(contagem, "rq07_classes_por_combinacao")
    comum.salvar_tabela(por_metrica.set_index(["par", "metrica"]), "rq07_mudanca_por_metrica")
    comum.salvar_tabela(transicoes_longas(todas).set_index(["par", "de", "para"]),
                        "rq07_transicoes")
    comum.salvar_figura(figura_classes(contagem), "rq07_classes_por_combinacao")


if __name__ == "__main__":  # pragma: no cover
    main()
