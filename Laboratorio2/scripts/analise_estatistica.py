"""
Análise estatística de RQ1, RQ2 e RQ3 — Lab 2, Sprint 3, Passo 4.

Pareamento: cada um dos 6 katas foi resolvido uma vez "manual" e uma vez "com
IA" por integrantes diferentes (rodízio contrabalanceado, ver README.md,
seção 6). O par manual/IA de cada kata é a unidade de comparação usada no
teste de Wilcoxon (amostras pareadas), consistente com o desenho
within-subject do experimento.

RQ3 compara complexidade ciclomática (Radon cc), índice de manutenibilidade
(Radon mi) e duplicação de código, sempre ao lado do LOC como métrica de
controle (código gerado por IA pode ser mais verboso, o que por si só
infla/reduz as demais métricas).

Além do que a especificação pede para RQ3, este módulo também analisa (como
aprofundamento do grupo): métricas de Halstead (volume, dificuldade, esforço,
bugs estimados — já coletadas pelo Radon desde a Sprint 1, mas não usadas até
aqui).

Métricas inspiradas em CK (WMC, DIT, NOC, CBO, RFC, LCOM) foram avaliadas e
descartadas: a maioria mede relação entre classes (herança, acoplamento,
coesão), e cada kata aqui é uma única classe `Solution` de método único —
DIT/NOC saíam constantes em 0 e LCOM só era definido em 1 dos 12 trials, sem
dado relevante para a análise.
"""

import json
import statistics
import warnings
from pathlib import Path

from scipy.stats import wilcoxon

from consolidar_dados import carregar_trials

RAIZ = Path(__file__).parent.parent

_METRICAS_RQ3 = {
    "cc_media": "Complexidade ciclomática média (Radon cc)",
    "mi": "Índice de manutenibilidade (Radon mi)",
    "loc": "Linhas de código (LOC) - métrica de controle",
    "duplicacao_pct": "Duplicação de código (%)",
}

_METRICAS_HALSTEAD = {
    "hal_volume": "Halstead - Volume",
    "hal_dificuldade": "Halstead - Dificuldade",
    "hal_esforco": "Halstead - Esforço",
    "hal_bugs_estimados": "Halstead - Bugs estimados (estimativa estática, não empírica)",
}

_METRICAS_LOC = {
    "loc": "LOC total",
    "ncloc": "NCLOC (total - branco - comentário)",
    "loc_branco": "LOC em branco",
    "loc_comentario": "LOC comentário",
    "loc_diretivas": "LOC diretivas (import)",
    "loc_decl": "LOC declarativas (assinatura de classe/função)",
    "loc_exec": "LOC executáveis",
}

def _mediana_iqr(valores: list[float]) -> dict:
    quantis = statistics.quantiles(valores, n=4, method="inclusive")
    return {
        "mediana": round(statistics.median(valores), 2),
        "q1": round(quantis[0], 2),
        "q3": round(quantis[2], 2),
        "iqr": round(quantis[2] - quantis[0], 2),
        "n": len(valores),
    }


def _pares_por_kata(linhas: list[dict], campo: str) -> tuple[list[float], list[float]]:
    por_kata = {}
    for linha in linhas:
        por_kata.setdefault(linha["kata_id"], {})[linha["tratamento"]] = linha[campo]

    manual, ia = [], []
    for kata_id in sorted(por_kata):
        valores = por_kata[kata_id]
        manual.append(valores["manual"])
        ia.append(valores["ia"])
    return manual, ia


def _wilcoxon_pareado(manual: list[float], ia: list[float]) -> dict:
    diffs = [m - i for m, i in zip(manual, ia)]
    if all(d == 0 for d in diffs):
        return {
            "aplicavel": False,
            "motivo": "todas as diferenças pareadas são zero (sem variação entre tratamentos)",
        }
    with warnings.catch_warnings(record=True) as avisos_capturados:
        warnings.simplefilter("always")
        estatistica, p_valor = wilcoxon(manual, ia)
        avisos = [str(a.message) for a in avisos_capturados]

    resultado = {
        "aplicavel": True,
        "estatistica": round(float(estatistica), 4),
        "p_valor": round(float(p_valor), 4),
        "significativo_a_5pct": bool(p_valor < 0.05),
    }
    if avisos:
        # Esperado com N=6 (amostra pequena, como previsto na especificação):
        # scipy recorre à aproximação normal em vez da distribuição exata.
        resultado["aviso_amostra_pequena"] = avisos
    return resultado


def _analisar_metrica(linhas: list[dict], campo: str, descricao: str) -> dict:
    manual = [l[campo] for l in linhas if l["tratamento"] == "manual"]
    ia = [l[campo] for l in linhas if l["tratamento"] == "ia"]
    manual_pareado, ia_pareado = _pares_por_kata(linhas, campo)

    return {
        "metrica": descricao,
        "manual": _mediana_iqr(manual),
        "ia": _mediana_iqr(ia),
        "wilcoxon_pareado_por_kata": _wilcoxon_pareado(manual_pareado, ia_pareado),
    }


def analisar_rq1(linhas: list[dict]) -> dict:
    manual_pareado, ia_pareado = _pares_por_kata(linhas, "tempo_segundos")
    return {
        "rq": "RQ1 - Tempo até passar em todos os testes de aceitação (segundos)",
        "manual": _mediana_iqr(manual_pareado),
        "ia": _mediana_iqr(ia_pareado),
        "wilcoxon_pareado_por_kata": _wilcoxon_pareado(manual_pareado, ia_pareado),
        "trials_censurados": sum(1 for l in linhas if l["censurado"]),
    }


def analisar_rq2(linhas: list[dict]) -> dict:
    manual_pareado, ia_pareado = _pares_por_kata(linhas, "taxa_sucesso")
    return {
        "rq": "RQ2 - Taxa de sucesso dos testes de aceitação ao final do time-box (%)",
        "manual": _mediana_iqr(manual_pareado),
        "ia": _mediana_iqr(ia_pareado),
        "wilcoxon_pareado_por_kata": _wilcoxon_pareado(manual_pareado, ia_pareado),
        "testes_falhando_total": sum(l["testes_total"] - l["testes_passados"] for l in linhas),
    }


def analisar_rq3(linhas: list[dict]) -> dict:
    resultado = {
        "rq": "RQ3 - Complexidade ciclomática e duplicação do código produzido",
    }
    for campo, descricao in _METRICAS_RQ3.items():
        resultado[campo] = _analisar_metrica(linhas, campo, descricao)

    # cc normalizada por LOC (evita que a verbosidade de um tratamento explique
    # sozinha uma cc média maior/menor).
    for linha in linhas:
        linha["_cc_por_100_loc"] = round(100 * linha["cc_media"] / linha["loc"], 2) if linha["loc"] else 0.0
    resultado["cc_normalizada_por_100_loc"] = _analisar_metrica(
        linhas, "_cc_por_100_loc", "Complexidade ciclomática média por 100 LOC"
    )

    return resultado


def analisar_halstead(linhas: list[dict]) -> dict:
    resultado = {
        "rq": "Aprofundamento - Métricas de Halstead (além da especificação, que só pede MI opcional)",
    }
    for campo, descricao in _METRICAS_HALSTEAD.items():
        resultado[campo] = _analisar_metrica(linhas, campo, descricao)
    return resultado


def analisar_loc(linhas: list[dict]) -> dict:
    resultado = {
        "rq": "Aprofundamento - Classificação de LOC por tipo (além da especificação, que só pede LOC total)",
    }
    for campo, descricao in _METRICAS_LOC.items():
        resultado[campo] = _analisar_metrica(linhas, campo, descricao)
    return resultado


def main():
    linhas = carregar_trials()
    resultado = {
        "rq1_tempo": analisar_rq1(linhas),
        "rq2_defeitos": analisar_rq2(linhas),
        "rq3_estrutura": analisar_rq3(linhas),
        "aprofundamento_halstead": analisar_halstead(linhas),
        "aprofundamento_loc": analisar_loc(linhas),
    }

    saida = RAIZ / "resultados"
    saida.mkdir(exist_ok=True)
    (saida / "analise_estatistica.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print("\nSalvo em resultados/analise_estatistica.json")


if __name__ == "__main__":
    main()
