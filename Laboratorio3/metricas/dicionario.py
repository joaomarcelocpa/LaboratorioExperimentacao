"""Gera docs/dicionario_dados.md a partir de SCHEMAS.

O enunciado exige que cada coluna dos CSVs finais seja documentada com nome,
tipo, unidade e fórmula ou origem na API. Gerar o documento a partir do
código impede que a documentação envelheça: um teste compara o arquivo em
disco com a saída desta função.

Uso: python -m metricas.dicionario
"""
from __future__ import annotations

from pathlib import Path

from metricas.schemas import SCHEMAS, Schema

CAMINHO_PADRAO = Path(__file__).resolve().parent.parent / "docs" / "dicionario_dados.md"

_CABECALHO = """# Dicionário de dados

> **Arquivo gerado.** Não edite à mão: rode `python -m metricas.dicionario`.
> A fonte é `metricas/schemas.py`.

Convenções de todo o estudo:

- Chave de todo CSV: `repo`, no formato `owner/nome`.
- Datas em ISO 8601 UTC.
- Durações em horas.
- Proporções em 0–1.
- Valor ausente é vazio no CSV (`NaN` ao ler com pandas) e significa que a
  métrica não pôde ser calculada para aquele repositório.
"""


def _escapar(texto: str) -> str:
    """Um | solto quebraria a tabela Markdown."""
    return texto.replace("|", r"\|")


def _tabela(schema: Schema) -> str:
    linhas = [
        f"## `{schema.nome}`",
        "",
        f"**Dono:** {schema.dono}",
        "",
        "| Coluna | Tipo | Unidade | Origem |",
        "|---|---|---|---|",
    ]
    for nome, meta in schema.colunas.items():
        linhas.append(
            f"| `{nome}` | {_escapar(meta.tipo)} | {_escapar(meta.unidade)} "
            f"| {_escapar(meta.origem)} |"
        )
    linhas.append("")
    return "\n".join(linhas)


def gerar_markdown() -> str:
    partes = [_CABECALHO]
    for chave in sorted(SCHEMAS):
        partes.append(_tabela(SCHEMAS[chave]))
    return "\n".join(partes)


def main() -> None:
    CAMINHO_PADRAO.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_PADRAO.write_text(gerar_markdown(), encoding="utf-8")
    print(f"gerado: {CAMINHO_PADRAO}")


if __name__ == "__main__":
    main()
