"""Esquema do CSV por passo (PLANEJAMENTO.pdf, seção 3.5).

O esquema é congelado desde o piloto: as 32 colunas, a ordem e os tipos abaixo
não mudam entre piloto e coleta completa. A documentação humana está em
docs/s01/esquema-de-dados.md; este módulo é a versão executável dela.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

MODOS = ("incremental", "regenerado")
PASSO_MAX = 10
TIPOS_PEDIDO = ("semente", "cabe", "tensiona")
STATUS = ("ok", "falha")


@dataclass(frozen=True)
class Coluna:
    nome: str
    tipo: str  # int | float | str | bool01
    unidade: str
    regra: str
    anulavel: bool = False


# Campos que descrevem o produto no fim do passo. Ficam vazios quando o passo
# falha (status = falha): não há workspace utilizável para medir.
_MEDIDAS = True

COLUNAS: tuple[Coluna, ...] = (
    Coluna("chain_id", "int", "índice", "1..K. O mesmo índice nos dois modos identifica o par da análise pareada."),
    Coluna("mode", "str", "categoria", "incremental | regenerado."),
    Coluna("step", "int", "passo", "0 a 10. Passo 0 é a semente (linha-base, sem execução do agente)."),
    Coluna("request_id", "str", "texto", "P0 a P10. No modo regenerado, o último pedido incluído no prompt acumulado."),
    Coluna("request_type", "str", "categoria", "semente (passo 0) | cabe | tensiona, conforme a marcação do pedido."),
    Coluna("timestamp", "str", "ISO 8601 UTC", "Fim da execução do passo, p.ex. 2026-11-20T14:03:11Z."),
    Coluna("tool_version", "str", "versão", "Versão exata do Claude Code (claude --version). Constante na coleta."),
    Coluna("model_id", "str", "id", "Modelo fixado explicitamente. Constante na coleta."),
    Coluna("tokens_in", "int", "tokens", "Tokens de entrada somados em todos os turnos, incluindo cache.", True),
    Coluna("tokens_out", "int", "tokens", "Tokens de saída somados em todos os turnos.", True),
    Coluna("cost_usd", "float", "USD", "Custo reportado pelo Claude Code no JSON de saída.", True),
    Coluna("duration_s", "float", "segundos", "Duração de parede da execução, em segundos.", True),
    Coluna("turns", "int", "contagem", "Número de turnos do agente.", True),
    Coluna("agent_ran_tests", "bool01", "0/1", "1 se o transcript mostra o agente rodando testes por conta própria.", True),
    Coluna("run_ok", "bool01", "0/1", "1 se a execução terminou sem erro nem tempo esgotado (tentativa final)."),
    Coluna("retry", "bool01", "0/1", "1 se houve a tentativa extra permitida (a primeira falhou)."),
    Coluna("build_ok", "bool01", "0/1", "1 se o build compila no fim do passo.", True),
    Coluna("boot_ok", "bool01", "0/1", "1 se docker compose sobe e /health responde 200.", True),
    Coluna("reg_total", "int", "contagem", "Testes de regressão executados (HTTP e interface).", True),
    Coluna("reg_failed", "int", "contagem", "Testes de regressão que falham nas DUAS rodadas.", True),
    Coluna("acc_total", "int", "contagem", "Testes de aceitação do pedido atual.", True),
    Coluna("acc_failed", "int", "contagem", "Testes de aceitação do pedido atual que falham nas duas rodadas.", True),
    Coluna("flaky", "int", "contagem", "Testes (regressão + aceitação) com resultado diferente entre as duas rodadas.", True),
    Coluna("arch_violations", "int", "contagem", "Violações ArchUnit no estado do workspace (não é delta).", True),
    Coluna("cycles", "int", "contagem", "Ciclos entre pacotes no grafo de dependências.", True),
    Coluna("files_touched", "int", "contagem", "Arquivos do diff do commit do passo.", True),
    Coluna("modules_touched", "int", "contagem", "Módulos (pacotes de topo) tocados no diff do commit.", True),
    Coluna("max_ccn", "int", "complexidade", "Maior complexidade ciclomática de uma função (Lizard).", True),
    Coluna("dup_pct", "float", "%", "Percentual de linhas duplicadas (jscpd), 0 a 100.", True),
    Coluna("loc", "int", "linhas", "Linhas de código Java de src/main (Lizard nloc: sem testes, brancos nem comentários).", True),
    Coluna("doc_drift", "int", "contagem", "Deriva documento × código: regras do ARCHITECTURE.md violadas + módulos não documentados.", True),
    Coluna("status", "str", "categoria", "ok | falha. falha = erro/tempo esgotado/build quebrado também após a nova tentativa."),
)

NOMES = tuple(c.nome for c in COLUNAS)
_POR_NOME = {c.nome: c for c in COLUNAS}
INTEIRAS = tuple(c.nome for c in COLUNAS if c.tipo in ("int", "bool01"))
FLOATS = tuple(c.nome for c in COLUNAS if c.tipo == "float")
BOOLEANAS = tuple(c.nome for c in COLUNAS if c.tipo == "bool01")
ANULAVEIS = tuple(c.nome for c in COLUNAS if c.anulavel)
CONTAGENS_NAO_NEGATIVAS = (
    "tokens_in", "tokens_out", "turns", "reg_total", "reg_failed", "acc_total", "acc_failed",
    "flaky", "arch_violations", "cycles", "files_touched", "modules_touched", "max_ccn", "loc", "doc_drift",
)


def carregar(caminho) -> pd.DataFrame:
    """Lê um CSV por passo com os tipos do esquema (inteiros anuláveis viram Int64)."""
    df = pd.read_csv(caminho)
    return normalizar_tipos(df)


def normalizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for nome in INTEIRAS:
        if nome in df.columns:
            df[nome] = pd.to_numeric(df[nome], errors="coerce").astype("Int64")
    for nome in FLOATS:
        if nome in df.columns:
            df[nome] = pd.to_numeric(df[nome], errors="coerce")
    return df


def validar(df: pd.DataFrame) -> list[str]:
    """Devolve a lista de problemas encontrados (vazia = CSV válido).

    Verifica colunas e ordem, domínios, faixas, nulos e as regras entre colunas
    que a análise assume (cadeia contígua, sem linhas após falha, etc.).
    """
    erros: list[str] = []
    if tuple(df.columns) != NOMES:
        faltam = [c for c in NOMES if c not in df.columns]
        sobram = [c for c in df.columns if c not in NOMES]
        if faltam:
            erros.append(f"colunas ausentes: {faltam}")
        if sobram:
            erros.append(f"colunas fora do esquema: {sobram}")
        if not faltam and not sobram:
            erros.append("colunas fora da ordem do esquema")
        if faltam:
            return erros  # sem as colunas não dá para checar o resto
    df = normalizar_tipos(df)

    for nome in NOMES:
        c = _POR_NOME[nome]
        if not c.anulavel and df[nome].isna().any():
            erros.append(f"{nome}: valores vazios em {int(df[nome].isna().sum())} linha(s)")

    if not df["mode"].isin(MODOS).all():
        erros.append(f"mode fora de {MODOS}")
    if not df["request_type"].isin(TIPOS_PEDIDO).all():
        erros.append(f"request_type fora de {TIPOS_PEDIDO}")
    if not df["status"].isin(STATUS).all():
        erros.append(f"status fora de {STATUS}")
    if not df["step"].between(0, PASSO_MAX).all():
        erros.append(f"step fora de 0..{PASSO_MAX}")
    for nome in BOOLEANAS:
        if not df[nome].dropna().isin([0, 1]).all():
            erros.append(f"{nome}: deve ser 0 ou 1")
    for nome in CONTAGENS_NAO_NEGATIVAS:
        if (df[nome].dropna() < 0).any():
            erros.append(f"{nome}: valor negativo")
    for nome in ("cost_usd", "duration_s"):
        if (df[nome].dropna() < 0).any():
            erros.append(f"{nome}: valor negativo")
    if not df["dup_pct"].dropna().between(0, 100).all():
        erros.append("dup_pct fora de 0..100")

    if df.duplicated(["chain_id", "mode", "step"]).any():
        erros.append("há (chain_id, mode, step) repetido")
    for nome in ("tool_version", "model_id"):
        if df[nome].nunique() > 1:
            erros.append(f"{nome} muda ao longo da coleta ({sorted(df[nome].unique())}); registre como desvio")

    ok = df[df["status"] == "ok"]
    if (ok["reg_failed"] > ok["reg_total"]).any():
        erros.append("reg_failed maior que reg_total")
    if (ok["acc_failed"] > ok["acc_total"]).any():
        erros.append("acc_failed maior que acc_total")
    if (ok["modules_touched"] > ok["files_touched"]).any():
        erros.append("modules_touched maior que files_touched")
    if ok[[n for n in ANULAVEIS if n not in ("tokens_in", "tokens_out", "cost_usd", "duration_s", "turns", "agent_ran_tests")]].isna().any().any():
        erros.append("passo com status ok tem medida do produto vazia")
    if ((df["retry"] == 0) & (df["run_ok"] == 0)).any():
        erros.append("run_ok = 0 sem retry = 1 (a falha exige a nova tentativa)")
    falhas = df[df["status"] == "falha"]
    if (falhas["run_ok"].eq(1) & falhas["build_ok"].fillna(0).eq(1)).any():
        erros.append("status falha com run_ok = 1 e build_ok = 1")

    for (cadeia, modo), g in df.groupby(["chain_id", "mode"]):
        g = g.sort_values("step")
        passos = g["step"].tolist()
        if passos[0] != 0:
            erros.append(f"cadeia {cadeia}/{modo}: falta o passo 0")
        if passos != list(range(len(passos))):
            erros.append(f"cadeia {cadeia}/{modo}: passos não contíguos {passos}")
        if (g["status"] == "falha").any():
            primeiro = g[g["status"] == "falha"]["step"].min()
            if (g["step"] > primeiro).any():
                erros.append(f"cadeia {cadeia}/{modo}: há passos depois da falha no passo {primeiro}")
        base = g[g["step"] == 0]
        if len(base) and base["request_type"].iloc[0] != "semente":
            erros.append(f"cadeia {cadeia}/{modo}: passo 0 deve ter request_type = semente")
    return erros
