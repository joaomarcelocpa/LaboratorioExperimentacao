"""
Script de análise de métricas de código usando Radon.

Métricas coletadas por arquivo Python:
  - cc  : complexidade ciclomática (por função/método)
  - mi  : índice de manutenibilidade
  - raw : linhas de código (LOC, LLOC, SLOC, comentários, em branco)

Uso:
  python metricas_radon.py <caminho>          # arquivo ou diretório
  python metricas_radon.py <caminho> -o saida.json
"""

import argparse
import json
import sys
from pathlib import Path

from radon.complexity import cc_visit, average_complexity, cc_rank
from radon.metrics import mi_visit
from radon.raw import analyze


def _analisar_arquivo(caminho: Path) -> dict:
    codigo = caminho.read_text(encoding="utf-8", errors="replace")

    # complexidade ciclomática por bloco (função/método/classe)
    blocos_cc = cc_visit(codigo)
    cc_por_bloco = [
        {
            "nome": bloco.name,
            "tipo": bloco.letter,
            "linha": bloco.lineno,
            "complexidade": bloco.complexity,
            "rank": cc_rank(bloco.complexity),
        }
        for bloco in blocos_cc
    ]
    cc_media = average_complexity(blocos_cc) if blocos_cc else 0.0

    # índice de manutenibilidade
    mi_resultado = mi_visit(codigo, multi=True)

    # métricas brutas de linhas
    raw = analyze(codigo)

    return {
        "arquivo": str(caminho),
        "cc": {
            "media": round(cc_media, 2),
            "blocos": cc_por_bloco,
        },
        "mi": {
            "valor": round(mi_resultado, 2),
        },
        "raw": {
            "loc": raw.loc,
            "lloc": raw.lloc,
            "sloc": raw.sloc,
            "comentarios": raw.comments,
            "linhas_em_branco": raw.blank,
            "multi_linha": raw.multi,
        },
    }


def analisar(caminho: str) -> list[dict]:
    alvo = Path(caminho)
    if not alvo.exists():
        raise FileNotFoundError(f"Caminho não encontrado: {caminho}")

    arquivos = (
        sorted(alvo.rglob("*.py"))
        if alvo.is_dir()
        else [alvo]
    )

    resultados = []
    for arq in arquivos:
        try:
            resultados.append(_analisar_arquivo(arq))
        except Exception as exc:
            resultados.append({"arquivo": str(arq), "erro": str(exc)})

    return resultados


def main():
    parser = argparse.ArgumentParser(description="Analisa métricas de código Python com Radon")
    parser.add_argument("caminho", help="Arquivo .py ou diretório a analisar")
    parser.add_argument("-o", "--output", help="Arquivo JSON de saída (padrão: stdout)")
    args = parser.parse_args()

    resultados = analisar(args.caminho)
    saida = json.dumps(resultados, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(saida, encoding="utf-8")
        print(f"Métricas salvas em: {args.output}")
    else:
        print(saida)


if __name__ == "__main__":
    main()
