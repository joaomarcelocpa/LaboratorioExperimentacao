"""Contratos de dados: a fonte única de verdade dos CSVs do estudo.

Este dicionário alimenta três consumidores — o validador, o gerador do
dicionário de dados e as fixtures de teste — para que documentação e código
não possam divergir.

Chave de todo CSV: `repo` em owner/nome. Datas ISO 8601 UTC. Durações em
horas. Proporções em 0–1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

NOTAS_DORA = {"Low": 1, "Medium": 2, "High": 3, "Elite": 4}


class ErroDeContrato(Exception):
    """CSV ou DataFrame que não respeita o contrato."""


@dataclass(frozen=True)
class Coluna:
    tipo: str
    unidade: str
    origem: str


@dataclass(frozen=True)
class Schema:
    nome: str
    dono: str
    colunas: dict[str, Coluna]
    regras: list[Callable[[pd.DataFrame], list[str]]] = field(default_factory=list)


# --- regras semânticas ---------------------------------------------------

def _classe_coerente(df: pd.DataFrame) -> list[str]:
    """classe_dora (texto) e classe_dora_nota (1-4) dizem a mesma coisa."""
    erros = []
    if "classe_dora" not in df.columns or "classe_dora_nota" not in df.columns:
        return erros
    for i, linha in df.iterrows():
        classe, nota = linha.get("classe_dora"), linha.get("classe_dora_nota")
        if pd.isna(classe) or pd.isna(nota):
            continue
        if classe not in NOTAS_DORA:
            erros.append(f"linha {i}: classe_dora '{classe}' não é Elite/High/Medium/Low")
        elif NOTAS_DORA[classe] != int(nota):
            erros.append(
                f"linha {i}: classe_dora '{classe}' esperava "
                f"classe_dora_nota {NOTAS_DORA[classe]}, encontrado {int(nota)}"
            )
    return erros


def _notas_no_intervalo(df: pd.DataFrame) -> list[str]:
    erros = []
    for col in ["nota_freq", "nota_lead_time", "nota_cfr",
                "nota_recuperacao", "classe_dora_nota"]:
        if col not in df.columns:
            continue
        fora = df[col].dropna()
        fora = fora[(fora < 1) | (fora > 4)]
        for i, v in fora.items():
            erros.append(f"linha {i}: {col}={v} fora do intervalo 1-4")
    return erros


def _mes_pobre_e_nulo(df: pd.DataFrame) -> list[str]:
    """Mês com menos de 5 runs válidos tem métricas nulas (RQ 08b)."""
    erros = []
    if "runs_validos" not in df.columns:
        return erros
    pobres = df[df["runs_validos"] < 5]
    for i, linha in pobres.iterrows():
        for col in ("cfr_a", "recuperacao_h"):
            if col in df.columns and not pd.isna(linha[col]):
                erros.append(
                    f"linha {i}: runs_validos={linha['runs_validos']} (<5) "
                    f"exige {col} nulo, encontrado {linha[col]}"
                )
    return erros


# --- contratos -----------------------------------------------------------

def _c(tipo: str, unidade: str, origem: str) -> Coluna:
    return Coluna(tipo=tipo, unidade=unidade, origem=origem)


_REPO = _c("str", "owner/nome", "chave do estudo")

SCHEMAS: dict[str, Schema] = {
    "candidatos": Schema("candidatos.csv", "A", {
        "repo": _REPO,
        "estrelas": _c("int", "contagem", "search/repositories: stargazers_count"),
        "faixa_estrelas": _c("str", "intervalo", "fatia de busca do config.yaml"),
    }),
    "repos": Schema("repos.csv", "A", {
        "repo": _REPO,
        "estrelas": _c("int", "contagem", "repos/{owner}/{repo}: stargazers_count"),
        "linguagem": _c("str", "nome", "repos/{owner}/{repo}: language"),
        "criado_em": _c("data", "ISO 8601 UTC", "repos/{owner}/{repo}: created_at"),
        "idade_anos": _c("float", "anos", "janela.fim - criado_em"),
        "default_branch": _c("str", "nome", "repos/{owner}/{repo}: default_branch"),
        "contribuidores": _c("int", "contagem", "contributors?per_page=1&anon=true: última página do Link"),
        "owner_tipo": _c("str", "User|Organization", "repos/{owner}/{repo}: owner.type"),
        "org_verificada": _c("bool", "sim/não", "orgs/{org}: is_verified"),
        "automacao_release": _c("bool", "sim/não", "presença de .releaserc*, release-please-config.json, .changeset/ ou .goreleaser.y*ml"),
        "ferramenta_release": _c("str", "nome", "semantic-release|release-please|changesets|goreleaser|nenhuma"),
        "pct_conventional": _c("float", "proporção 0-1", "% de commits.mensagem que casam com o regex de Conventional Commits"),
    }),
    "funil": Schema("funil.csv", "A", {
        "etapa": _c("str", "nome", "etapa do filtro de seleção"),
        "entraram": _c("int", "contagem", "repositórios na entrada da etapa"),
        "sairam": _c("int", "contagem", "repositórios descartados na etapa"),
        "motivo": _c("str", "texto", "razão do descarte"),
    }),
    "descartes": Schema("descartes.csv", "A", {
        "repo": _REPO,
        "etapa": _c("str", "nome", "etapa do funil em que caiu"),
        "motivo": _c("str", "texto", "razão do descarte"),
    }),
    "issues_bug": Schema("issues_bug.csv", "A", {
        "repo": _REPO,
        "numero": _c("int", "contagem", "issues: number"),
        "criada_em": _c("data", "ISO 8601 UTC", "issues: created_at"),
        "labels": _c("str", "lista separada por ;", "issues: labels[].name"),
        "titulo": _c("str", "texto", "issues: title"),
        "cita_tag": _c("bool", "sim/não", "título ou corpo cita a tag de uma release"),
    }),
    "releases": Schema("releases.csv", "B", {
        "repo": _REPO,
        "tag": _c("str", "nome", "releases: tag_name"),
        "publicada_em": _c("data", "ISO 8601 UTC", "releases: published_at"),
        "prerelease": _c("bool", "sim/não", "releases: prerelease"),
        "na_janela": _c("bool", "sim/não", "publicada_em dentro de janela"),
        "body": _c("str", "texto", "releases: body (release notes)"),
    }),
    "releases_ignoradas": Schema("releases_ignoradas.csv", "B", {
        "repo": _REPO,
        "tag": _c("str", "nome", "releases: tag_name"),
        "motivo": _c("str", "texto", "404 no compare, sem release anterior etc."),
    }),
    "tags": Schema("tags.csv", "B", {
        "repo": _REPO,
        "tag": _c("str", "nome", "tags: name"),
        "sha": _c("str", "sha1", "tags: commit.sha"),
        "data_commit": _c("data", "ISO 8601 UTC", "commits/{sha}: commit.author.date"),
    }),
    "commits": Schema("commits.csv", "B", {
        "repo": _REPO,
        "release_tag": _c("str", "nome", "release que inclui o commit"),
        "sha": _c("str", "sha1", "compare: commits[].sha"),
        "data_autor": _c("data", "ISO 8601 UTC", "compare: commits[].commit.author.date"),
        "autor_login": _c("str", "login", "compare: commits[].author.login"),
        "eh_bot": _c("bool", "sim/não", "login termina em [bot] ou está em config.bots"),
        "mensagem": _c("str", "texto", "compare: commits[].commit.message"),
    }),
    "deployments": Schema("deployments.csv", "B", {
        "repo": _REPO,
        "id": _c("int", "identificador", "deployments: id"),
        "environment": _c("str", "nome", "deployments: environment"),
        "criado_em": _c("data", "ISO 8601 UTC", "deployments: created_at"),
        "sha": _c("str", "sha1", "deployments: sha"),
        "estado_final": _c("str", "success|failure|...", "deployments/{id}/statuses: state"),
    }),
    "runs": Schema("runs.csv", "C", {
        "repo": _REPO,
        "run_id": _c("int", "identificador", "actions/runs: id"),
        "workflow_id": _c("int", "identificador", "actions/runs: workflow_id"),
        "workflow_nome": _c("str", "nome", "actions/runs: name"),
        "event": _c("str", "push|schedule|...", "actions/runs: event"),
        "head_sha": _c("str", "sha1", "actions/runs: head_sha"),
        "run_attempt": _c("int", "contagem", "actions/runs: run_attempt"),
        "conclusion": _c("str", "success|failure|...", "actions/runs: conclusion"),
        "classe": _c("str", "sucesso|falha|ignorado", "tabela de conclusion da seção 3 do enunciado"),
        "inicio": _c("data", "ISO 8601 UTC", "actions/runs: run_started_at"),
        "fim": _c("data", "ISO 8601 UTC", "actions/runs: updated_at"),
    }),
    "run_attempts": Schema("run_attempts.csv", "C", {
        "repo": _REPO,
        "run_id": _c("int", "identificador", "actions/runs: id"),
        "tentativa": _c("int", "contagem", "actions/runs/{id}/attempts/{n}: run_attempt"),
        "conclusion": _c("str", "success|failure|...", "attempts/{n}: conclusion"),
        "inicio": _c("data", "ISO 8601 UTC", "attempts/{n}: run_started_at"),
        "fim": _c("data", "ISO 8601 UTC", "attempts/{n}: updated_at"),
    }),
    "episodios": Schema("episodios.csv", "C", {
        "repo": _REPO,
        "workflow_id": _c("int", "identificador", "runs.workflow_id"),
        "inicio": _c("data", "ISO 8601 UTC", "run_started_at da primeira falha"),
        "fim": _c("data", "ISO 8601 UTC", "updated_at do próximo sucesso"),
        "horas": _c("float", "horas", "fim - inicio"),
        "censurado": _c("bool", "sim/não", "episódio sem sucesso até o fim da janela"),
        "so_flaky": _c("bool", "sim/não", "falha e sucesso no mesmo head_sha"),
    }),
    "custo_api": Schema("custo_api.csv", "C", {
        "endpoint": _c("str", "caminho", "endpoint chamado"),
        "chamadas": _c("int", "contagem", "chamadas que saíram da máquina"),
        "do_cache": _c("int", "contagem", "respostas servidas pelo cache"),
    }),
    "metricas": Schema("metricas.csv", "Todos", {
        "repo": _REPO,
        "freq_release": _c("float", "releases/semana", "RQ01: releases na janela ÷ 52,1"),
        "freq_release_pre": _c("float", "releases/semana", "RQ01 variante: releases + pré-releases ÷ 52,1"),
        "freq_tag": _c("float", "tags/semana", "RQ01 variante: tags ÷ 52,1"),
        "freq_deploy": _c("float", "deploys/semana", "RQ01 variante: deployments em produção ÷ 52,1"),
        "lt_release_h": _c("float", "horas", "RQ02a: mediana de (data da release - commit mais antigo)"),
        "lt_commit_h": _c("float", "horas", "RQ02b: mediana por commit"),
        "lt_commit_sem_bots_h": _c("float", "horas", "RQ02b excluindo commits de bot"),
        "pct_commits_bot": _c("float", "proporção 0-1", "commits de bot ÷ total de commits"),
        "cfr_a": _c("float", "proporção 0-1", "RQ03a: falhas ÷ (falhas + sucessos) na conclusion listada"),
        "cfr_a_bruto": _c("float", "proporção 0-1", "RQ03a incluindo tentativas anteriores"),
        "cfr_a_sem_flaky": _c("float", "proporção 0-1", "RQ03a removendo falhas seguidas de sucesso no mesmo head_sha"),
        "cfr_b": _c("float", "proporção 0-1", "RQ03b: releases seguidas de corretiva em 7 dias ÷ releases avaliadas"),
        "cfr_c": _c("float", "proporção 0-1", "RQ03c: releases seguidas de issue de bug em n_dias_issue"),
        "recuperacao_h": _c("float", "horas", "RQ04: mediana dos episódios de falha"),
        "recuperacao_sem_flaky_h": _c("float", "horas", "RQ04 ignorando episódios só de flaky"),
        "pct_censurados": _c("float", "proporção 0-1", "episódios censurados ÷ total de episódios"),
        "recuperacao_releases_h": _c("float", "horas", "horas entre a release que falhou e a corretiva"),
        "rework_rate": _c("float", "proporção 0-1", "RQ08a: releases corretivas ÷ releases avaliadas, sem limite de dias"),
        "rework_rate_7d": _c("float", "proporção 0-1", "RQ08a variante: corretiva em até 7 dias da anterior"),
        "nota_freq": _c("int", "1-4", "tabela de cortes DORA sobre freq_release"),
        "nota_lead_time": _c("int", "1-4", "tabela de cortes DORA sobre lt_release_h"),
        "nota_cfr": _c("int", "1-4", "tabela de cortes DORA sobre cfr_a"),
        "nota_recuperacao": _c("int", "1-4", "tabela de cortes DORA sobre recuperacao_h"),
        "classe_dora": _c("str", "Elite|High|Medium|Low", "mediana das quatro notas, arredondada para baixo"),
        "classe_dora_nota": _c("int", "1-4", "a mesma mediana, como inteiro, para o kappa ponderado da RQ07"),
    }, regras=[_classe_coerente, _notas_no_intervalo]),
    "metricas_mensais": Schema("metricas_mensais.csv", "C", {
        "repo": _REPO,
        "mes": _c("mes", "AAAA-MM", "mês da janela"),
        "cfr_a": _c("float", "proporção 0-1", "RQ08b: CFR de CI do mês; NaN se runs_validos < 5"),
        "recuperacao_h": _c("float", "horas", "RQ08b: mediana do tempo de recuperação no mês; NaN se runs_validos < 5"),
        "runs_validos": _c("int", "contagem", "runs de sucesso + falha no mês"),
    }, regras=[_mes_pobre_e_nulo]),
}


# --- validação -----------------------------------------------------------

_CHECAGEM = {
    "int": pd.api.types.is_numeric_dtype,
    "float": pd.api.types.is_numeric_dtype,
    "bool": lambda s: pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s),
    "str": lambda s: pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s),
    "data": lambda s: pd.api.types.is_object_dtype(s)
    or pd.api.types.is_string_dtype(s)
    or pd.api.types.is_datetime64_any_dtype(s),
    "mes": lambda s: pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s),
}


def validar(df: pd.DataFrame, schema: Schema, estrito: bool = True) -> None:
    """Valida um DataFrame contra o contrato.

    Estrito por padrão: coluna fora do schema é erro, porque o grupo
    replicador compara coluna a coluna e o enunciado exige que toda coluna
    esteja no dicionário de dados.
    """
    erros: list[str] = []

    faltando = [c for c in schema.colunas if c not in df.columns]
    if faltando:
        erros.append(f"colunas faltando: {', '.join(sorted(faltando))}")

    if estrito:
        sobrando = [c for c in df.columns if c not in schema.colunas]
        if sobrando:
            erros.append(
                f"colunas fora do contrato: {', '.join(sorted(sobrando))}. "
                f"Acrescente-as a metricas/schemas.py e regenere "
                f"docs/dicionario_dados.md no mesmo commit."
            )

    for col, meta in schema.colunas.items():
        if col not in df.columns or df[col].empty:
            continue
        if not _CHECAGEM[meta.tipo](df[col]):
            erros.append(
                f"coluna '{col}': esperado {meta.tipo}, "
                f"encontrado {df[col].dtype}"
            )

    if not faltando:
        for regra in schema.regras:
            erros.extend(regra(df))

    if erros:
        raise ErroDeContrato(f"{schema.nome}: " + "; ".join(erros))


def validar_csv(caminho: str | Path, schema: Schema, estrito: bool = True) -> None:
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroDeContrato(f"{schema.nome}: arquivo não encontrado: {caminho}")
    validar(pd.read_csv(caminho), schema, estrito=estrito)


def df_vazio(schema: Schema) -> pd.DataFrame:
    """DataFrame sem linhas, com as colunas do contrato."""
    return pd.DataFrame({col: [] for col in schema.colunas})
