import csv
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "repositorios.csv"
DEFAULT_OUTPUT_RQ04_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "bernardo" / "rq04-validada.csv"
DEFAULT_OUTPUT_RQ05_PATH = Path(__file__).resolve().parent.parent.parent / "dados" / "bernardo" / "rq05-linguagens.csv"

TODAY = datetime.now(tz=timezone.utc)

RQ04_HEADER = ["coluna", "valores_ausentes", "total_linhas", "media_dias", "mediana_dias", "qtd_outliers"]
RQ05_HEADER = ["linguagem", "quantidade", "percentual"]


def _detect_outliers_iqr(values: list[float]) -> int:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n < 4:
        return 0
    q1 = statistics.median(sorted_vals[: n // 2])
    q3 = statistics.median(sorted_vals[(n + 1) // 2 :])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return sum(1 for v in sorted_vals if v < lower or v > upper)


def validar_rq04(rows: list[dict]) -> dict:
    ausentes = 0
    dias_list = []

    for row in rows:
        raw = row.get("atualizado_em", "")
        if not raw or not raw.strip():
            ausentes += 1
            continue
        try:
            dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            dias_list.append((TODAY - dt).days)
        except ValueError:
            ausentes += 1

    return {
        "coluna": "atualizado_em",
        "valores_ausentes": ausentes,
        "total_linhas": len(rows),
        "media_dias": round(statistics.mean(dias_list), 2) if dias_list else "",
        "mediana_dias": statistics.median(dias_list) if dias_list else "",
        "qtd_outliers": _detect_outliers_iqr(dias_list) if dias_list else 0,
    }


def validar_rq05(rows: list[dict]) -> list[dict]:
    total = len(rows)
    ausentes = 0
    counter: Counter = Counter()

    for row in rows:
        lang = row.get("linguagem", "")
        if not lang or not lang.strip():
            ausentes += 1
        else:
            counter[lang.strip()] += 1

    results = [
        {
            "linguagem": lang,
            "quantidade": count,
            "percentual": round(count / total * 100, 2),
        }
        for lang, count in counter.most_common()
    ]

    if ausentes:
        results.append({
            "linguagem": "(sem linguagem)",
            "quantidade": ausentes,
            "percentual": round(ausentes / total * 100, 2),
        })

    return results


if __name__ == "__main__":
    with open(DEFAULT_INPUT_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    DEFAULT_OUTPUT_RQ04_PATH.parent.mkdir(parents=True, exist_ok=True)

    rq04 = validar_rq04(rows)
    with open(DEFAULT_OUTPUT_RQ04_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RQ04_HEADER)
        writer.writeheader()
        writer.writerow(rq04)

    rq05 = validar_rq05(rows)
    with open(DEFAULT_OUTPUT_RQ05_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RQ05_HEADER)
        writer.writeheader()
        writer.writerows(rq05)

    print(
        f"RQ04 (atualizado_em): ausentes={rq04['valores_ausentes']}/{rq04['total_linhas']} "
        f"media={rq04['media_dias']}d mediana={rq04['mediana_dias']}d outliers={rq04['qtd_outliers']}"
    )
    print(f"\nRQ05 (linguagem): {len(rq05)} linguagens distintas")
    for r in rq05[:10]:
        print(f"  {r['linguagem']}: {r['quantidade']} repos ({r['percentual']}%)")

    print(f"\nRQ04 salvo em {DEFAULT_OUTPUT_RQ04_PATH}")
    print(f"RQ05 salvo em {DEFAULT_OUTPUT_RQ05_PATH}")
