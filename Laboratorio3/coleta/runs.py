"""Coleta das execuções de CI do default branch.

A listagem de /actions/runs devolve no máximo 1.000 resultados por consulta,
então a janela é fatiada em meses e cada fatia que satura é partida ao meio
até caber. Partir um mês dá quinzenas; partir uma quinzena dá semanas.

As funções daqui produzem linhas já no formato dos contratos runs.csv e
run_attempts.csv. Quem escreve os CSVs é o orquestrador (#39), e quem calcula
CFR e tempo de recuperação é a #42.
"""
from __future__ import annotations

import calendar
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd

# Importado como módulo, e não as funções: é isso que faz redefinir_cliente
# nos testes valer para as chamadas feitas daqui.
from coleta import http
from metricas.schemas import SCHEMAS, validar

MAX_TENTATIVAS_PADRAO = 5
TETO_POR_CONSULTA = 1000          # máximo de resultados por consulta filtrada
PISO_DA_FATIA = timedelta(hours=1)
CAMINHO_FATIAS = "data/processed/fatias_saturadas.csv"
API = "https://api.github.com"

_log = logging.getLogger(__name__)

# Tabela da seção 3 do enunciado. O que não está aqui é ignorado — um
# conclusion novo não pode inflar o CFR sozinho.
_CLASSES = {
    "success": "sucesso",
    "failure": "falha",
    "timed_out": "falha",
    "startup_failure": "falha",
    "cancelled": "ignorado",
    "skipped": "ignorado",
    "neutral": "ignorado",
    "action_required": "ignorado",
    "stale": "ignorado",
}

_desconhecidas: Counter[str] = Counter()


def classificar(conclusion: str | None) -> str:
    """Sucesso, falha ou ignorado, pela tabela da seção 3.

    Tem um efeito colateral de propósito: valores fora da tabela são contados
    e o primeiro de cada um é logado. A alternativa, devolver
    (classe, desconhecido), contaminaria os chamadores da #42, que só querem
    a classe. O valor de retorno não depende do contador.
    """
    bruto = (conclusion or "").strip().lower()
    if not bruto:
        return "ignorado"
    if bruto in _CLASSES:
        return _CLASSES[bruto]
    if bruto not in _desconhecidas:
        _log.warning(
            "conclusion desconhecido na API: %r. Tratado como 'ignorado'. "
            "Se virar comum, acrescente a _CLASSES em coleta/runs.py.",
            bruto,
        )
    _desconhecidas[bruto] += 1
    return "ignorado"


def desconhecidas() -> dict[str, int]:
    """Valores de conclusion fora da tabela, com quantas vezes apareceram."""
    return dict(_desconhecidas)


def esquecer_desconhecidas() -> None:
    _desconhecidas.clear()


def iso(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


def _comeco(dia: date) -> datetime:
    return datetime.combine(dia, time(0, 0, 0), tzinfo=timezone.utc)


def _fim(dia: date) -> datetime:
    return datetime.combine(dia, time(23, 59, 59), tzinfo=timezone.utc)


@dataclass(frozen=True)
class Fatia:
    """Intervalo fechado nas duas pontas: [inicio, fim]."""

    inicio: datetime
    fim: datetime

    def duracao(self) -> timedelta:
        # +1 s porque o fim é fechado: 00:00:00..00:59:59 é uma hora cheia.
        return self.fim - self.inicio + timedelta(seconds=1)

    def e_de_dias_inteiros(self) -> bool:
        return (
            self.inicio.time() == time(0, 0, 0)
            and self.fim.time() == time(23, 59, 59)
        )

    def created(self) -> str:
        """Valor do parâmetro created= da API.

        A forma de data é a do enunciado e é a que a API aceita com certeza;
        a forma com hora só aparece abaixo de um dia, quando a subdivisão
        precisa descer mais.
        """
        if self.e_de_dias_inteiros():
            return f"{self.inicio.date().isoformat()}..{self.fim.date().isoformat()}"
        return f"{iso(self.inicio)}..{iso(self.fim)}"

    def partir(self) -> tuple["Fatia", "Fatia"] | None:
        """Duas metades sem buraco e sem sobreposição, ou None no piso."""
        if self.duracao() <= PISO_DA_FATIA:
            return None
        meio = (self.inicio + self.duracao() / 2).replace(microsecond=0)
        if meio <= self.inicio or meio > self.fim:
            return None
        return (
            Fatia(self.inicio, meio - timedelta(seconds=1)),
            Fatia(meio, self.fim),
        )


def meses(inicio: date, fim: date) -> list[Fatia]:
    """A janela em fatias de mês-calendário, recortadas nas pontas.

    O recorte importa: uma janela que começa no dia 15 não pode render uma
    fatia que começa no dia 1, senão a coleta puxa runs de fora da janela e
    enviesa a amostra inteira.
    """
    if fim < inicio:
        raise ValueError(f"fim ({fim}) é anterior a inicio ({inicio})")

    fatias: list[Fatia] = []
    atual = inicio
    while atual <= fim:
        ultimo_do_mes = atual.replace(
            day=calendar.monthrange(atual.year, atual.month)[1]
        )
        fatias.append(Fatia(_comeco(atual), _fim(min(ultimo_do_mes, fim))))
        atual = ultimo_do_mes + timedelta(days=1)
    return fatias


@dataclass(frozen=True)
class FatiaSaturada:
    """Fatia que bateu o teto e não pôde ser subdividida.

    É ameaça à validade, não ruído de log: parte dos runs daquele intervalo
    ficou de fora e o artigo precisa dizer isso.
    """

    repo: str
    inicio: str
    fim: str
    total_count: int


@dataclass(frozen=True)
class Coleta:
    runs: list[dict]
    saturadas: list[FatiaSaturada]


def _linha_de_run(repo: str, item: dict) -> dict:
    """Item da API no formato do contrato runs.csv."""
    return {
        "repo": repo,
        "run_id": item["id"],
        "workflow_id": item.get("workflow_id"),
        "workflow_nome": item.get("name"),
        "event": item.get("event"),
        "head_sha": item.get("head_sha"),
        # Um run sem run_attempt é a primeira tentativa. int(None) estouraria.
        "run_attempt": int(item.get("run_attempt") or 1),
        "conclusion": item.get("conclusion"),
        "classe": classificar(item.get("conclusion")),
        "inicio": item.get("run_started_at"),
        "fim": item.get("updated_at"),
        "criado_em": item.get("created_at"),
    }


def _saturada(repo: str, fatia: Fatia, total: int) -> FatiaSaturada:
    return FatiaSaturada(repo, iso(fatia.inicio), iso(fatia.fim), total)


def coletar_runs(
    repo: str, default_branch: str, inicio: date, fim: date
) -> Coleta:
    """Runs de push do default branch na janela, fatiados até caberem.

    O teto de 1.000 é da consulta, não da página: paginar até o fim devolve
    1.000 e descarta o resto sem avisar. Por isso a saturação é detectada por
    total_count, e a primeira página da sondagem vira acerto de cache quando
    a fatia cabe — nenhuma chamada é desperdiçada no caminho normal.
    """
    url = f"{API}/repos/{repo}/actions/runs"
    linhas: dict[int, dict] = {}
    saturadas: list[FatiaSaturada] = []
    # (fatia, total da fatia-mãe) — a mãe é o que sabemos quando um 422
    # impede de medir a filha.
    pendentes: list[tuple[Fatia, int]] = [(f, 0) for f in meses(inicio, fim)]

    while pendentes:
        fatia, total_da_mae = pendentes.pop()
        filtros = {
            "branch": default_branch,
            "event": "push",
            "created": fatia.created(),
        }

        try:
            sondagem = http.get(url, {**filtros, "per_page": 100})
        except http.ErroDeHTTP as e:
            if e.status == 422 and not fatia.e_de_dias_inteiros():
                # A API recusou created= com hora: a recursão para aqui.
                saturadas.append(_saturada(repo, fatia, total_da_mae))
                continue
            raise

        carga = sondagem.json()
        if "total_count" not in carga:
            raise KeyError(
                f"resposta de {url} sem 'total_count'; sem ele não dá para "
                f"saber se a fatia {fatia.created()} saturou"
            )
        total = int(carga["total_count"])

        if total == 0:
            continue

        if total >= TETO_POR_CONSULTA:
            metades = fatia.partir()
            if metades is not None:
                pendentes.extend((m, total) for m in metades)
                continue
            # No piso: registra e colhe o que der.
            saturadas.append(_saturada(repo, fatia, total))

        for item in http.paginar(url, filtros):
            linhas[item["id"]] = _linha_de_run(repo, item)

    return Coleta(list(linhas.values()), saturadas)


def df_runs(linhas: list[dict]) -> pd.DataFrame:
    """DataFrame no contrato de runs.csv, validado antes de sair."""
    df = pd.DataFrame(linhas, columns=list(SCHEMAS["runs"].colunas))
    validar(df, SCHEMAS["runs"])
    return df


def escrever_fatias_saturadas(
    saturadas: list[FatiaSaturada], caminho: str | Path = CAMINHO_FATIAS
) -> Path:
    """Grava o diagnóstico de fatias que não couberam.

    Fora de SCHEMAS de propósito: é artefato de diagnóstico, não dataset de
    análise, então não passa por validar nem entra no dicionário de dados.
    """
    df = pd.DataFrame(
        [
            {"repo": f.repo, "inicio": f.inicio, "fim": f.fim,
             "total_count": f.total_count}
            for f in saturadas
        ],
        columns=["repo", "inicio", "fim", "total_count"],
    )
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False)
    return caminho
