"""Valida a INTEGRIDADE dos dados brutos que alimentam RQ06 e RQ07.

Escopo: apenas as colunas usadas por RQ06 (razão issues fechadas/total) e
RQ07 (mergedPRs, releasesCount, tempo desde pushedAt, agrupados por
primaryLanguage). Não calcula métricas nem testa hipóteses — isso é
trabalho de análise, feito em uma etapa posterior.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent / "dados" / "miguel" / "repos_raw.csv"
EXPECTED_ROWS = 1000

# Mapeia nomes lógicos para os nomes reais das colunas no CSV coletado via GraphQL.
COLS: dict[str, str] = {
    "name_with_owner": "nameWithOwner",
    "closed_issues": "closedIssues",
    "total_issues": "totalIssues",
    "merged_prs": "mergedPRs",
    "releases_count": "releasesCount",
    "pushed_at": "pushedAt",
    "primary_language": "primaryLanguage",
}

REQUIRED_NON_NULL = [
    COLS["name_with_owner"],
    COLS["closed_issues"],
    COLS["total_issues"],
    COLS["merged_prs"],
    COLS["releases_count"],
    COLS["pushed_at"],
]
NULLABLE_COLS = [COLS["primary_language"]]
SCOPE_COLS = REQUIRED_NON_NULL + NULLABLE_COLS


def construir_schema() -> pa.DataFrameSchema:
    """Camada 1: schema pandera para as colunas do escopo (RQ06/RQ07)."""
    return pa.DataFrameSchema(
        {
            COLS["name_with_owner"]: pa.Column(str, nullable=False, unique=True, coerce=True),
            COLS["closed_issues"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["total_issues"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["merged_prs"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["releases_count"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["pushed_at"]: pa.Column(str, nullable=False, coerce=True),
            COLS["primary_language"]: pa.Column(str, nullable=True, coerce=True),
        },
        checks=pa.Check(
            lambda df: df[COLS["closed_issues"]] <= df[COLS["total_issues"]],
            error="closedIssues <= totalIssues",
        ),
    )


def validar_schema(df: pd.DataFrame) -> tuple[bool, list[dict[str, Any]]]:
    """Camada 1: roda o schema pandera (lazy) e devolve (ok, erros)."""
    schema = construir_schema()
    try:
        schema.validate(df, lazy=True)
        return True, []
    except pa.errors.SchemaErrors as exc:
        erros = exc.failure_cases.astype(object).where(exc.failure_cases.notna(), None)
        return False, erros.to_dict(orient="records")


def contar_nulos_por_coluna(df: pd.DataFrame) -> dict[str, int]:
    """Camada 2: conta nulos por coluna do escopo (completude)."""
    return {coluna: int(df[coluna].isna().sum()) for coluna in SCOPE_COLS if coluna in df.columns}


def linhas_pushed_at_invalido(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Camada 2: linhas cujo pushedAt não é uma data ISO-8601 parseável."""
    coluna = COLS["pushed_at"]
    chave = COLS["name_with_owner"]
    if coluna not in df.columns:
        return []
    original = df[coluna]
    parseado = pd.to_datetime(original, errors="coerce", utc=True)
    invalido = parseado.isna() & original.notna()
    return [
        {"nameWithOwner": row.get(chave), "pushedAt": row.get(coluna)}
        for row in df.loc[invalido, [chave, coluna]].to_dict(orient="records")
    ]


def linhas_pushed_at_futuro(df: pd.DataFrame, agora: pd.Timestamp | None = None) -> list[dict[str, Any]]:
    """Camada 2: linhas cujo pushedAt está no futuro em relação a `agora`."""
    coluna = COLS["pushed_at"]
    chave = COLS["name_with_owner"]
    if coluna not in df.columns:
        return []
    referencia = agora if agora is not None else pd.Timestamp.now(tz="UTC")
    parseado = pd.to_datetime(df[coluna], errors="coerce", utc=True)
    futuro = parseado > referencia
    linhas = df.loc[futuro, [chave]].copy()
    linhas[coluna] = parseado.loc[futuro].astype(str)
    return [
        {"nameWithOwner": row.get(chave), "pushedAt": row.get(coluna)}
        for row in linhas.to_dict(orient="records")
    ]


def verificar_volume(n_linhas: int, esperado: int = EXPECTED_ROWS) -> bool:
    """Camada 2: confere se o número de linhas bate com o esperado da coleta."""
    return n_linhas == esperado


def gerar_relatorio(
    df: pd.DataFrame,
    *,
    strict: bool = False,
    agora: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Roda todos os checks de integridade sobre `df` e monta o relatório final."""
    schema_ok, schema_erros = validar_schema(df)
    nulos_por_coluna = contar_nulos_por_coluna(df)
    pushed_at_invalido = linhas_pushed_at_invalido(df)
    pushed_at_futuro = linhas_pushed_at_futuro(df, agora=agora)
    n_linhas = len(df)
    volume_ok = verificar_volume(n_linhas)

    erros_bloqueantes = (
        not schema_ok
        or bool(pushed_at_invalido)
        or bool(pushed_at_futuro)
        or (strict and not volume_ok)
    )

    return {
        "arquivo_linhas": n_linhas,
        "linhas_esperadas": EXPECTED_ROWS,
        "volume_ok": volume_ok,
        "schema_ok": schema_ok,
        "schema_erros": schema_erros,
        "nulos_por_coluna": nulos_por_coluna,
        "pushed_at_invalido": pushed_at_invalido,
        "pushed_at_futuro": pushed_at_futuro,
        "status": "FALHA" if erros_bloqueantes else "OK",
    }


def imprimir_relatorio(relatorio: dict[str, Any]) -> None:
    """Imprime o relatório em formato legível no stdout."""
    print(f"Linhas no CSV: {relatorio['arquivo_linhas']} (esperado: {relatorio['linhas_esperadas']})")
    print(f"Volume: {'OK' if relatorio['volume_ok'] else 'DIVERGENTE'}")

    print(f"Schema (tipos, domínio >=0, closedIssues<=totalIssues, unicidade): "
          f"{'OK' if relatorio['schema_ok'] else 'FALHA'}")
    if not relatorio["schema_ok"]:
        for erro in relatorio["schema_erros"]:
            print(f"  - coluna={erro.get('column')} check={erro.get('check')} "
                  f"index={erro.get('index')} valor={erro.get('failure_case')}")

    print("Nulos por coluna:")
    for coluna, qtd in relatorio["nulos_por_coluna"].items():
        marcador = " (aceitável)" if coluna == COLS["primary_language"] else ""
        print(f"  - {coluna}: {qtd}{marcador}")

    if relatorio["pushed_at_invalido"]:
        print(f"pushedAt não parseável: {len(relatorio['pushed_at_invalido'])} linha(s)")
        for item in relatorio["pushed_at_invalido"]:
            print(f"  - {item['nameWithOwner']}: {item['pushedAt']}")

    if relatorio["pushed_at_futuro"]:
        print(f"pushedAt no futuro: {len(relatorio['pushed_at_futuro'])} linha(s)")
        for item in relatorio["pushed_at_futuro"]:
            print(f"  - {item['nameWithOwner']}: {item['pushedAt']}")

    print(f"\nStatus final: {relatorio['status']}")


def validar_arquivo(caminho: Path, *, strict: bool = False) -> dict[str, Any]:
    """Lê o CSV em `caminho` e roda o relatório de integridade sobre ele."""
    try:
        df = pd.read_csv(caminho)
    except Exception as exc:  # noqa: BLE001 - qualquer falha de leitura vira mensagem clara
        print(f"Erro ao ler CSV '{caminho}': {exc}", file=sys.stderr)
        sys.exit(1)

    colunas_ausentes = [c for c in SCOPE_COLS if c not in df.columns]
    if colunas_ausentes:
        print(f"Erro: colunas do escopo ausentes no CSV: {colunas_ausentes}", file=sys.stderr)
        sys.exit(1)

    return gerar_relatorio(df, strict=strict)


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="Valida a integridade dos dados brutos de RQ06/RQ07 (issues, PRs, releases, pushedAt, linguagem)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Caminho do CSV de entrada")
    parser.add_argument("--json", type=Path, default=None, help="Caminho para salvar o relatório em JSON")
    parser.add_argument("--strict", action="store_true", help="Trata número de linhas != 1000 como erro")
    args = parser.parse_args(argv)

    relatorio = validar_arquivo(args.input, strict=args.strict)
    imprimir_relatorio(relatorio)

    if args.json:
        args.json.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRelatório salvo em {args.json}")

    return 0 if relatorio["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# GitHub Actions (comentado) — roda a cada push e sobe o relatório JSON:
#
# name: Validar integridade RQ06/RQ07
# on: [push]
# jobs:
#   validate:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - uses: actions/setup-python@v5
#         with:
#           python-version: "3.12"
#       - run: pip install -r scripts/requirements.txt
#       - run: python scripts/validate_rq06_rq07_integrity.py --json out.json --strict
#       - uses: actions/upload-artifact@v4
#         if: always()
#         with:
#           name: rq06-rq07-integrity-report
#           path: out.json
# ---------------------------------------------------------------------------
