"""Valida a INTEGRIDADE dos dados brutos que alimentam RQ06 e RQ07.

Escopo: apenas as colunas usadas por RQ06 (razão issues fechadas/total) e
RQ07 (prs_mergeadas, releases, tempo desde atualizado_em, agrupados por
linguagem). Não calcula métricas nem testa hipóteses — isso é trabalho de
análise, feito em uma etapa posterior.

As colunas reais vêm de `coleta.py` (Laboratorio1/dados/repositorios.csv),
que não expõe um `totalIssues` bruto nem uma chave única `nameWithOwner` —
por isso `_total_issues` (issues_abertas + issues_fechadas) e `_repo_key`
(autor + "/" + nome_repositorio) são calculados aqui apenas para permitir
os checks de integridade abaixo (domínio e unicidade), não para análise.

Limitação conhecida: RQ07 pede o tempo desde `pushedAt` (último push de
código), mas a coleta atual só grava `atualizado_em` (`updatedAt`, que também
muda por motivos alheios a código, como estrelas). Até a coleta expor
`pushedAt`, este validador trata `atualizado_em` como proxy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa

DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent / "dados" / "repositorios.csv"
DEFAULT_JSON_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "dados" / "miguel" / "rq06-rq07-integridade.json"
)
EXPECTED_ROWS = 1000

# Nomes reais das colunas no CSV gerado por coleta.py (dados/repositorios.csv).
COLS: dict[str, str] = {
    "autor": "autor",
    "nome_repositorio": "nome_repositorio",
    "issues_abertas": "issues_abertas",
    "issues_fechadas": "issues_fechadas",
    "prs_mergeadas": "prs_mergeadas",
    "releases": "releases",
    "atualizado_em": "atualizado_em",
    "linguagem": "linguagem",
}

# Colunas calculadas (não existem no CSV) apenas para viabilizar os checks de integridade.
REPO_KEY_COL = "_repo_key"
TOTAL_ISSUES_COL = "_total_issues"

REQUIRED_NON_NULL = [
    COLS["autor"],
    COLS["nome_repositorio"],
    COLS["issues_abertas"],
    COLS["issues_fechadas"],
    COLS["prs_mergeadas"],
    COLS["releases"],
    COLS["atualizado_em"],
]
NULLABLE_COLS = [COLS["linguagem"]]
SCOPE_COLS = REQUIRED_NON_NULL + NULLABLE_COLS


def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona as colunas calculadas `_repo_key` e `_total_issues` a uma cópia de `df`."""
    df = df.copy()

    autor = df[COLS["autor"]]
    nome = df[COLS["nome_repositorio"]]
    chave = autor.astype(str).str.strip() + "/" + nome.astype(str).str.strip()
    df[REPO_KEY_COL] = chave.where(autor.notna() & nome.notna(), None)

    abertas = pd.to_numeric(df[COLS["issues_abertas"]], errors="coerce")
    fechadas = pd.to_numeric(df[COLS["issues_fechadas"]], errors="coerce")
    df[TOTAL_ISSUES_COL] = abertas + fechadas

    return df


def construir_schema() -> pa.DataFrameSchema:
    """Camada 1: schema pandera para as colunas do escopo (RQ06/RQ07) + colunas calculadas."""
    return pa.DataFrameSchema(
        {
            REPO_KEY_COL: pa.Column(str, nullable=False, unique=True, coerce=True),
            COLS["issues_fechadas"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["issues_abertas"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            TOTAL_ISSUES_COL: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["prs_mergeadas"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["releases"]: pa.Column(int, pa.Check.ge(0), nullable=False, coerce=True),
            COLS["atualizado_em"]: pa.Column(str, nullable=False, coerce=True),
            COLS["linguagem"]: pa.Column(str, nullable=True, coerce=True),
        },
        checks=pa.Check(
            lambda df: df[COLS["issues_fechadas"]] <= df[TOTAL_ISSUES_COL],
            error="issues_fechadas <= total_issues (issues_abertas + issues_fechadas)",
        ),
    )


def validar_schema(df: pd.DataFrame) -> tuple[bool, list[dict[str, Any]]]:
    """Camada 1: roda o schema pandera (lazy) sobre `df` já preparado e devolve (ok, erros)."""
    schema = construir_schema()
    try:
        schema.validate(df, lazy=True)
        return True, []
    except pa.errors.SchemaErrors as exc:
        erros = exc.failure_cases.astype(object).where(exc.failure_cases.notna(), None)
        return False, erros.to_dict(orient="records")


def contar_nulos_por_coluna(df: pd.DataFrame) -> dict[str, int]:
    """Camada 2: conta nulos por coluna real do escopo (completude)."""
    return {coluna: int(df[coluna].isna().sum()) for coluna in SCOPE_COLS if coluna in df.columns}


def linhas_atualizado_em_invalido(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Camada 2: linhas cujo atualizado_em não é uma data ISO-8601 parseável."""
    coluna = COLS["atualizado_em"]
    if coluna not in df.columns:
        return []
    original = df[coluna]
    parseado = pd.to_datetime(original, errors="coerce", utc=True)
    invalido = parseado.isna() & original.notna()
    return [
        {"repo": row.get(REPO_KEY_COL), "atualizado_em": row.get(coluna)}
        for row in df.loc[invalido, [REPO_KEY_COL, coluna]].to_dict(orient="records")
    ]


def linhas_atualizado_em_futuro(df: pd.DataFrame, agora: pd.Timestamp | None = None) -> list[dict[str, Any]]:
    """Camada 2: linhas cujo atualizado_em está no futuro em relação a `agora`."""
    coluna = COLS["atualizado_em"]
    if coluna not in df.columns:
        return []
    referencia = agora if agora is not None else pd.Timestamp.now(tz="UTC")
    parseado = pd.to_datetime(df[coluna], errors="coerce", utc=True)
    futuro = parseado > referencia
    linhas = df.loc[futuro, [REPO_KEY_COL]].copy()
    linhas[coluna] = parseado.loc[futuro].astype(str)
    return [
        {"repo": row.get(REPO_KEY_COL), "atualizado_em": row.get(coluna)}
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
    """Roda todos os checks de integridade sobre `df` (colunas reais) e monta o relatório final."""
    df = preparar_dataframe(df)

    schema_ok, schema_erros = validar_schema(df)
    nulos_por_coluna = contar_nulos_por_coluna(df)
    pushed_at_invalido = linhas_atualizado_em_invalido(df)
    pushed_at_futuro = linhas_atualizado_em_futuro(df, agora=agora)
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

    print(f"Schema (tipos, domínio >=0, issues_fechadas<=total, unicidade): "
          f"{'OK' if relatorio['schema_ok'] else 'FALHA'}")
    if not relatorio["schema_ok"]:
        for erro in relatorio["schema_erros"]:
            print(f"  - coluna={erro.get('column')} check={erro.get('check')} "
                  f"index={erro.get('index')} valor={erro.get('failure_case')}")

    print("Nulos por coluna:")
    for coluna, qtd in relatorio["nulos_por_coluna"].items():
        marcador = " (aceitável)" if coluna == COLS["linguagem"] else ""
        print(f"  - {coluna}: {qtd}{marcador}")

    if relatorio["pushed_at_invalido"]:
        print(f"atualizado_em não parseável: {len(relatorio['pushed_at_invalido'])} linha(s)")
        for item in relatorio["pushed_at_invalido"]:
            print(f"  - {item['repo']}: {item['atualizado_em']}")

    if relatorio["pushed_at_futuro"]:
        print(f"atualizado_em no futuro: {len(relatorio['pushed_at_futuro'])} linha(s)")
        for item in relatorio["pushed_at_futuro"]:
            print(f"  - {item['repo']}: {item['atualizado_em']}")

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
        description="Valida a integridade dos dados brutos de RQ06/RQ07 (issues, PRs, releases, atualizado_em, linguagem)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Caminho do CSV de entrada")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON_OUTPUT_PATH, help="Caminho para salvar o relatório em JSON")
    parser.add_argument("--strict", action="store_true", help="Trata número de linhas != 1000 como erro")
    args = parser.parse_args(argv)

    relatorio = validar_arquivo(args.input, strict=args.strict)
    imprimir_relatorio(relatorio)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
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
#       - run: pip install -r Laboratorio1/scripts/requirements.txt
#       - run: python Laboratorio1/scripts/validate_rq06_rq07_integrity.py --strict
#       - uses: actions/upload-artifact@v4
#         if: always()
#         with:
#           name: rq06-rq07-integrity-report
#           path: Laboratorio1/dados/miguel/rq06-rq07-integridade.json
# ---------------------------------------------------------------------------
