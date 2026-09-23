"""
Script de análise de métricas de código usando Radon.

Métricas coletadas por arquivo Python:
  - cc  : complexidade ciclomática (por função/método)
  - mi  : índice de manutenibilidade
  - hal : métricas de Halstead (volume, dificuldade, esforço, bugs estimados)
  - raw : linhas de código (LOC, LLOC, SLOC, comentários, em branco)
  - dup : duplicação de código (blocos de >= MIN_DUP_LINES linhas repetidos)

"""

import argparse
import hashlib
import json
from pathlib import Path

from radon.complexity import cc_visit, average_complexity, cc_rank
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze

_MIN_DUP_LINES = 5


def _halstead(codigo: str) -> dict:
    relatorio = h_visit(codigo)
    total = relatorio.total

    return {
        "total": {
            "volume": round(total.volume, 2),
            "dificuldade": round(total.difficulty, 2),
            "esforco": round(total.effort, 2),
            "bugs_estimados": round(total.bugs, 4),
            "tempo_estimado_seg": round(total.time, 2),
        },
        "por_funcao": [
            {
                "nome": nome,
                "volume": round(metrica.volume, 2),
                "dificuldade": round(metrica.difficulty, 2),
                "esforco": round(metrica.effort, 2),
                "bugs_estimados": round(metrica.bugs, 4),
            }
            for nome, metrica in relatorio.functions
        ],
    }


def _analisar_arquivo(caminho: Path) -> dict:
    codigo = caminho.read_text(encoding="utf-8", errors="replace")

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

    mi_resultado = mi_visit(codigo, multi=True)

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
        "hal": _halstead(codigo),
        "raw": {
            "loc": raw.loc,
            "lloc": raw.lloc,
            "sloc": raw.sloc,
            "comentarios": raw.comments,
            "linhas_em_branco": raw.blank,
            "multi_linha": raw.multi,
        },
    }


def _linhas_significativas(caminho: Path) -> list[tuple[int, str]]:
    """Retorna (numero_linha, conteudo) das linhas não-vazias e não-comentário."""
    try:
        linhas = caminho.read_text(encoding="utf-8", errors="replace").splitlines()
        return [
            (i + 1, l.strip())
            for i, l in enumerate(linhas)
            if l.strip() and not l.strip().startswith("#")
        ]
    except Exception:
        return []


def _detectar_duplicatas(arquivos: list[Path]) -> dict:
    """
    Detecta blocos duplicados (>= _MIN_DUP_LINES linhas) dentro e entre arquivos
    usando janela deslizante com hash MD5. Equivalente funcional ao jscpd/PMD CPD
    para Python.
    """
    linhas_sig = {arq: _linhas_significativas(arq) for arq in arquivos}

    window_map: dict[str, list] = {}
    for arq, linhas in linhas_sig.items():
        n = len(linhas)
        for i in range(n - _MIN_DUP_LINES + 1):
            bloco = tuple(c for _, c in linhas[i : i + _MIN_DUP_LINES])
            h = hashlib.md5("".join(bloco).encode()).hexdigest()
            window_map.setdefault(h, []).append(
                (arq, linhas[i][0], linhas[i + _MIN_DUP_LINES - 1][0])
            )

    dup_lines: dict[Path, set] = {arq: set() for arq in arquivos}
    for ocorrencias in window_map.values():
        if len(ocorrencias) >= 2:
            for arq, ln_inicio, ln_fim in ocorrencias:
                dup_lines[arq].update(range(ln_inicio, ln_fim + 1))

    # calcula stats por arquivo e totais
    por_arquivo = {}
    total_sig = 0
    total_dup = 0
    for arq, linhas in linhas_sig.items():
        nums = {n for n, _ in linhas}
        sig = len(nums)
        dup = len(nums & dup_lines[arq])
        pct = round(100 * dup / sig, 2) if sig > 0 else 0.0
        por_arquivo[str(arq)] = {
            "linhas_significativas": sig,
            "linhas_duplicadas": dup,
            "percentual": pct,
        }
        total_sig += sig
        total_dup += dup

    return {
        "min_linhas_bloco": _MIN_DUP_LINES,
        "percentual_global": round(100 * total_dup / total_sig, 2) if total_sig > 0 else 0.0,
        "por_arquivo": por_arquivo,
    }


def analisar(caminho: str) -> dict:
    alvo = Path(caminho)
    if not alvo.exists():
        raise FileNotFoundError(f"Caminho não encontrado: {caminho}")

    arquivos = (
        sorted(alvo.rglob("*.py"))
        if alvo.is_dir()
        else [alvo]
    )

    metricas = []
    for arq in arquivos:
        try:
            metricas.append(_analisar_arquivo(arq))
        except Exception as exc:
            metricas.append({"arquivo": str(arq), "erro": str(exc)})

    return {
        "arquivos": metricas,
        "duplicacao": _detectar_duplicatas(arquivos),
    }


def main():
    parser = argparse.ArgumentParser(description="Analisa métricas de código Python com Radon")
    parser.add_argument("caminho", help="Arquivo .py ou diretório a analisar")
    parser.add_argument("-o", "--output", help="Arquivo JSON de saída (padrão: stdout)")
    args = parser.parse_args()

    resultado = analisar(args.caminho)
    saida = json.dumps(resultado, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(saida, encoding="utf-8")
        print(f"Métricas salvas em: {args.output}")
    else:
        print(saida)


if __name__ == "__main__":
    main()
