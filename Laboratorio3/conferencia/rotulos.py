"""Leitura e validação dos arquivos de rótulos preenchidos pelas pessoas.

Cada pessoa entrega rotulos_<nome>_repositorios.csv e rotulos_<nome>_releases.csv,
copias das planilhas geradas por conferencia.sorteio. Aqui tudo é conferido
antes de qualquer conta: uma resposta fora do vocabulário ou uma linha a menos
descoberta depois do kappa seria um número errado no artigo.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

VOCABULARIO = {
    "tipo_projeto": ["biblioteca", "aplicacao", "cli", "outro"],
    "entregas_reais": ["sim", "nao", "incerto"],
    "corretiva": ["sim", "nao"],
}

# tabela -> (chave, dimensões respondidas)
TABELAS = {
    "repositorios": (["repo"], ["tipo_projeto", "entregas_reais"]),
    "releases": (["repo", "tag"], ["corretiva"]),
}

_PADRAO = re.compile(r"^rotulos_(?P<nome>.+)_repositorios\.csv$")


class ErroDeRotulo(Exception):
    """Arquivo de rótulos ausente, incompleto ou com resposta inválida."""


def normalizar(valor: object) -> str:
    """'Não ' -> 'nao'. Aceita maiúscula e acento, mas nada além disso."""
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def descobrir_avaliadores(pasta: Path) -> list[str]:
    nomes = []
    for arq in sorted(Path(pasta).glob("rotulos_*_repositorios.csv")):
        m = _PADRAO.match(arq.name)
        if m:
            nomes.append(m.group("nome"))
    return nomes


def _ler(pasta: Path, nome: str, tabela: str) -> pd.DataFrame:
    caminho = Path(pasta) / f"rotulos_{nome}_{tabela}.csv"
    if not caminho.exists():
        raise ErroDeRotulo(f"falta o arquivo {caminho.name}")
    return pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def carregar(pasta: Path, avaliadores: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Retorna {tabela: DataFrame} com a chave e uma coluna '<dimensao>__<nome>'."""
    pasta = Path(pasta)
    avaliadores = avaliadores or descobrir_avaliadores(pasta)
    if len(avaliadores) < 2:
        raise ErroDeRotulo(
            f"preciso de ao menos 2 avaliadores em {pasta}; achei {avaliadores}"
        )

    saida: dict[str, pd.DataFrame] = {}
    problemas: list[str] = []
    for tabela, (chave, dimensoes) in TABELAS.items():
        referencia = pd.read_csv(
            pasta / f"planilha_{tabela}.csv", dtype=str, keep_default_na=False,
            encoding="utf-8-sig", usecols=chave,
        )
        esperado = set(map(tuple, referencia[chave].values))
        base = referencia.set_index(chave)
        for nome in avaliadores:
            df = _ler(pasta, nome, tabela)
            achado = set(map(tuple, df[chave].values))
            if achado != esperado or len(df) != len(esperado):
                problemas.append(
                    f"{nome}/{tabela}: linhas diferentes da planilha original "
                    f"(esperava {len(esperado)}, veio {len(df)}; "
                    f"faltam {len(esperado - achado)}, sobram {len(achado - esperado)})"
                )
                continue
            df = df.set_index(chave)
            for dim in dimensoes:
                valores = df[dim].map(normalizar)
                invalidos = df[~valores.isin(VOCABULARIO[dim])]
                for idx in invalidos.index[:5]:
                    problemas.append(
                        f"{nome}/{tabela}: '{df.loc[idx, dim]}' em {dim} (linha {idx}); "
                        f"use {VOCABULARIO[dim]}"
                    )
                if len(invalidos) > 5:
                    problemas.append(f"{nome}/{tabela}: mais {len(invalidos) - 5} em {dim}")
                base[f"{dim}__{nome}"] = valores.reindex(base.index)
        saida[tabela] = base
    if problemas:
        raise ErroDeRotulo("\n".join(problemas))
    return saida


def colunas_da_dimensao(df: pd.DataFrame, dimensao: str) -> list[str]:
    return [c for c in df.columns if c.startswith(f"{dimensao}__")]
