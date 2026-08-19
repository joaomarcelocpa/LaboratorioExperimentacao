import csv
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent / "dados" / "repositorios.csv"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "dados" / "joao" / "rqs-validadas.csv"

COLUMNS = ["criado_em", "prs_mergeadas", "releases"]

OUTPUT_HEADER = [
    "coluna",
    "valores_ausentes",
    "total_linhas",
    "media",
    "mediana",
    "qtd_outliers",
]


def _parse_criado_em(value):
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (dt - epoch).days


def _parse_numeric(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None


def _detect_outliers_iqr(pairs):
    """pairs: list of (row_label, numeric_value). Returns list of (row_label, value) outliers using IQR."""
    values = sorted(v for _, v in pairs)
    if len(values) < 4:
        return []
    q1 = statistics.median(values[: len(values) // 2])
    upper_half = values[(len(values) + 1) // 2:]
    q3 = statistics.median(upper_half)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return [(label, v) for label, v in pairs if v < lower_bound or v > upper_bound]


def validar_csv(input_path=DEFAULT_INPUT_PATH, output_path=DEFAULT_OUTPUT_PATH):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total_linhas = len(rows)
    resultados = []

    for coluna in COLUMNS:
        ausentes = 0
        pairs = []

        for row in rows:
            raw_value = row.get(coluna, "")
            label = f"{row.get('autor', '')}/{row.get('nome_repositorio', '')}"

            if raw_value is None or raw_value.strip() == "":
                ausentes += 1
                continue

            if coluna == "criado_em":
                numeric_value = _parse_criado_em(raw_value)
            else:
                numeric_value = _parse_numeric(raw_value)

            if numeric_value is None:
                ausentes += 1
                continue

            pairs.append((label, numeric_value))

        values = [v for _, v in pairs]

        if values:
            media = statistics.mean(values)
            mediana = statistics.median(values)
        else:
            media = ""
            mediana = ""

        outliers = _detect_outliers_iqr(pairs)

        if coluna == "criado_em":
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

            def fmt_days(d):
                return (epoch + timedelta(days=d)).strftime("%Y-%m-%d")

            media_fmt = fmt_days(media) if media != "" else ""
            mediana_fmt = fmt_days(mediana) if mediana != "" else ""
        else:
            media_fmt = round(media, 2) if media != "" else ""
            mediana_fmt = mediana

        resultados.append(
            {
                "coluna": coluna,
                "valores_ausentes": ausentes,
                "total_linhas": total_linhas,
                "media": media_fmt,
                "mediana": mediana_fmt,
                "qtd_outliers": len(outliers),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADER)
        writer.writeheader()
        writer.writerows(resultados)

    return resultados


if __name__ == "__main__":
    resultados = validar_csv()
    for r in resultados:
        print(
            f"{r['coluna']}: ausentes={r['valores_ausentes']}/{r['total_linhas']} "
            f"media={r['media']} mediana={r['mediana']} outliers={r['qtd_outliers']}"
        )
    print(f"\nResultado salvo em {DEFAULT_OUTPUT_PATH}")
