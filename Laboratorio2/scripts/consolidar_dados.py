"""
Consolidação dos dados do experimento (Lab 2 - Sprint 3).

Junta, por trial: tempo/taxa de sucesso (trials.csv de cada integrante) com as
métricas estáticas do Radon do arquivo de código correspondente
(metricas_<integrante>.json), usando katas.json para resolver dificuldade e
nome oficial do kata a partir do número do LeetCode.

Cada um dos 6 katas é resolvido exatamente uma vez "com IA" e uma vez "manual"
por integrantes diferentes (ver README.md, seção 6) — o pareamento para os
testes estatísticos (RQ1/RQ2/RQ3) é feito pelo kata, não pelo integrante.

Também calcula, por trial, métricas Halstead (já coletadas pelo Radon, mas
não usadas antes desta sprint) e a classificação de LOC por tipo (total,
branco, comentário, NCLOC, diretivas, declarativas, executáveis — via AST,
ver metricas_loc.py) — aprofundamento além do pedido pela especificação (RQ3
pede só cc/duplicação/LOC total, com MI como opcional).
"""

import csv
import json
from pathlib import Path

from metricas_loc import classificar_arquivo

RAIZ = Path(__file__).parent.parent
INTEGRANTES = ["joao", "bernardo", "miguel"]

# Miguel nomeou os arquivos pelo kata (não por tratamento/dificuldade como
# joao/bernardo), então o arquivo correspondente é resolvido por número do LeetCode.
ARQUIVO_POR_KATA_MIGUEL = {
    2011: "finalValueOfVariable.py",
    2255: "countPrefixes.py",
    306: "additiveNumber.py",
    654: "maxBinaryTree.py",
}

_DIFICULDADE_ARQUIVO = {"facil": "easy", "media": "medium", "medio": "medium"}


def _carregar_katas() -> dict:
    dados = json.loads((RAIZ / "scripts" / "katas.json").read_text(encoding="utf-8"))
    return {k["numero_leetcode"]: k for k in dados["katas"]}


def _parse_testes(valor: str) -> tuple[int, int]:
    """Converte '83/83' -> (83, 83) e '123' (trial não censurado) -> (123, 123)."""
    if "/" in valor:
        passados, total = valor.split("/")
        return int(passados), int(total)
    n = int(valor)
    return n, n


def _nome_arquivo(integrante: str, numero_leetcode: int, dificuldade: str, usou_ia: bool) -> str:
    if integrante == "miguel":
        return ARQUIVO_POR_KATA_MIGUEL[numero_leetcode]
    prefixo = "ai" if usou_ia else "manual"
    sufixo = _DIFICULDADE_ARQUIVO[dificuldade]
    return f"{prefixo}-{sufixo}.py"


def _indexar_metricas_por_arquivo(integrante: str) -> dict:
    caminho = RAIZ / "dados" / integrante / f"metricas_{integrante}.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))

    duplicacao_por_arquivo = {
        Path(arq.replace("\\", "/")).name: info
        for arq, info in dados["duplicacao"]["por_arquivo"].items()
    }

    indice = {}
    for arquivo in dados["arquivos"]:
        nome = Path(arquivo["arquivo"].replace("\\", "/")).name
        hal = arquivo["hal"]["total"]
        indice[nome] = {
            "cc_media": arquivo["cc"]["media"],
            "mi": arquivo["mi"]["valor"],
            "loc": arquivo["raw"]["loc"],
            "sloc": arquivo["raw"]["sloc"],
            "duplicacao_pct": duplicacao_por_arquivo.get(nome, {}).get("percentual", 0.0),
            "hal_volume": hal["volume"],
            "hal_dificuldade": hal["dificuldade"],
            "hal_esforco": hal["esforco"],
            "hal_bugs_estimados": hal["bugs_estimados"],
        }
    return indice


def carregar_trials() -> list[dict]:
    katas_por_numero = _carregar_katas()
    linhas = []

    for integrante in INTEGRANTES:
        metricas_arquivo = _indexar_metricas_por_arquivo(integrante)
        caminho_csv = RAIZ / "dados" / integrante / "trials.csv"

        with caminho_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                numero_leetcode = int(row["kata"].split(".", 1)[0])
                kata_info = katas_por_numero[numero_leetcode]
                usou_ia = row["usou_ia"] == "sim"
                passados, total = _parse_testes(row["testes_passados"])
                nome_arquivo = _nome_arquivo(
                    integrante, numero_leetcode, kata_info["dificuldade"], usou_ia
                )
                metricas = metricas_arquivo[nome_arquivo]
                loc_tipos = classificar_arquivo(RAIZ / "katas" / integrante / nome_arquivo)

                linhas.append(
                    {
                        "integrante": row["integrante"],
                        "kata_id": kata_info["id"],
                        "kata_nome": kata_info["nome"],
                        "numero_leetcode": numero_leetcode,
                        "dificuldade": kata_info["dificuldade"],
                        "tratamento": "ia" if usou_ia else "manual",
                        "tempo_segundos": int(row["tempo_segundos"]),
                        "censurado": row["censurado"] == "sim",
                        "testes_passados": passados,
                        "testes_total": total,
                        "taxa_sucesso": round(100 * passados / total, 2) if total else 0.0,
                        "cc_media": metricas["cc_media"],
                        "mi": metricas["mi"],
                        "loc": metricas["loc"],
                        "sloc": metricas["sloc"],
                        "duplicacao_pct": metricas["duplicacao_pct"],
                        "hal_volume": metricas["hal_volume"],
                        "hal_dificuldade": metricas["hal_dificuldade"],
                        "hal_esforco": metricas["hal_esforco"],
                        "hal_bugs_estimados": metricas["hal_bugs_estimados"],
                        "loc_branco": loc_tipos["loc_branco"],
                        "loc_comentario": loc_tipos["loc_comentario"],
                        "ncloc": loc_tipos["ncloc"],
                        "loc_diretivas": loc_tipos["loc_diretivas"],
                        "loc_decl": loc_tipos["loc_decl"],
                        "loc_exec": loc_tipos["loc_exec"],
                    }
                )

    linhas.sort(key=lambda l: (l["kata_id"], l["tratamento"]))
    return linhas


def main():
    linhas = carregar_trials()
    saida = RAIZ / "resultados"
    saida.mkdir(exist_ok=True)

    campos = list(linhas[0].keys())
    with (saida / "dados_consolidados.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(linhas)

    print(f"{len(linhas)} trials consolidados em resultados/dados_consolidados.csv")


if __name__ == "__main__":
    main()
