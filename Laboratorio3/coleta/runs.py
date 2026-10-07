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
PISO_DA_FATIA = timedelta(hours=1)   # nao se parte o que ja dura <= 1 h
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

        A forma de data é a do enunciado e é a que a API aceita com certeza.
        A forma com hora aparece assim que uma fatia deixa de terminar às
        23:59:59 — o que acontece já na PRIMEIRA divisão de um mês de 31
        dias, que parte em 15,5 dias. Não é um caso raro de fundo de
        recursão: 7 dos 12 meses de uma janela caem nela de cara. Por isso o
        422 na forma com hora é tratado como degradação esperada, e não como
        imprevisto.
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
    # Runs que a API devolveu fora do intervalo pedido. Deveria ser sempre 0:
    # qualquer outro número quer dizer que o created= não foi respeitado, e aí
    # a amostra tem runs de fora da janela.
    fora_da_fatia: int = 0


def _momento(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _linha_de_run(repo: str, item: dict) -> dict:
    """Item da API no formato do contrato runs.csv."""
    return {
        "repo": repo,
        "run_id": item["id"],
        # Estrito de propósito: com workflow_id nulo em parte das linhas, o
        # pandas coage a coluna para float e o CSV sai com 7.0 — e a #42
        # agrupa episódios de falha por esse campo.
        "workflow_id": item["workflow_id"],
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


def _e_degradavel(erro: http.ErroDeHTTP) -> bool:
    """Erro que vira diagnóstico em vez de derrubar o repositório.

    422 é o created= com hora recusado ou o teto de paginação; 403 é Actions
    desligado ou repositório sem acesso. Em ambos, perder os meses já
    coletados seria pior do que registrar a fatia e seguir. Um 401 continua
    estourando: esconder um token errado atrás de um CSV vazio é pior ainda.
    """
    return erro.status in (403, 422)


def _dentro(fatia: Fatia, created_at: str | None) -> bool:
    """O run está mesmo no intervalo pedido?

    Sem data não dá para afirmar que está fora, então conta como dentro.
    """
    momento = _momento(created_at)
    if momento is None:
        return True
    return fatia.inicio <= momento <= fatia.fim


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
    fora = 0
    # (fatia, total da fatia-mãe) — a mãe é o que sabemos quando um erro
    # impede de medir a filha, e é com ela que se vê se dividir adiantou.
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
            if _e_degradavel(e):
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
            # Se a filha devolve o mesmo tanto que a mãe, o created= não está
            # mordendo: continuar dividindo custaria milhares de chamadas sem
            # estreitar nada.
            estreitou = total_da_mae == 0 or total < total_da_mae
            metades = fatia.partir() if estreitou else None
            if metades is not None:
                pendentes.extend((m, total) for m in metades)
                continue
            # No piso, ou sem ganho em dividir: registra e colhe o que der.
            saturadas.append(_saturada(repo, fatia, total))

        try:
            itens = http.paginar(url, filtros)
        except http.ErroDeHTTP as e:
            if _e_degradavel(e):
                saturadas.append(_saturada(repo, fatia, total))
                continue
            raise

        for item in itens:
            if not _dentro(fatia, item.get("created_at")):
                fora += 1
            linhas[item["id"]] = _linha_de_run(repo, item)

    if fora:
        _log.warning(
            "%s: %s runs vieram fora da fatia pedida. O created= não foi "
            "respeitado e a amostra pode conter runs de fora da janela.",
            repo, fora,
        )

    return Coleta(list(linhas.values()), saturadas, fora)


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


_podadas: Counter[str] = Counter()


def tentativas_podadas() -> dict[str, int]:
    """Quantas tentativas o teto cortou e quantas a API já não tinha."""
    return {
        "cortadas_pelo_teto": _podadas["cortadas_pelo_teto"],
        "ausentes_na_api": _podadas["ausentes_na_api"],
    }


def esquecer_tentativas_podadas() -> None:
    _podadas.clear()


def coletar_tentativas(
    repo: str, runs: list[dict], max_tentativas: int = MAX_TENTATIVAS_PADRAO
) -> list[dict]:
    """Tentativas anteriores dos runs que foram rerodados.

    A listagem de /actions/runs mostra só a última tentativa, então as
    anteriores só existem em /attempts/{k}. Quando o teto corta, ficam as
    MAIS RECENTES: é o rerun imediatamente anterior que diz se uma falha foi
    instabilidade ou defeito.

    IMPORTANTE para quem consome: isto devolve as tentativas 1..n-1. A
    tentativa n, a última, NÃO está aqui — ela é a linha do próprio run em
    runs.csv. Quem for somar as tentativas de um run (o cfr_a_bruto da #42)
    precisa juntar as duas fontes, senão conta a mais ou a menos.
    """
    linhas: list[dict] = []

    for run in runs:
        total = int(run.get("run_attempt") or 1)
        if total <= 1:
            continue

        run_id = run["run_id"]
        primeira = max(1, total - max_tentativas)
        if primeira > 1:
            cortadas = primeira - 1
            _podadas["cortadas_pelo_teto"] += cortadas
            _log.warning(
                "run %s tem %s tentativas; o teto de %s deixou de fora as %s "
                "mais antigas.", run_id, total, max_tentativas, cortadas,
            )

        for k in range(primeira, total):
            resposta = http.get(f"{API}/repos/{repo}/actions/runs/{run_id}/attempts/{k}")
            if resposta.status == 404:
                # O GitHub poda tentativas antigas. Conta e segue.
                _podadas["ausentes_na_api"] += 1
                continue
            item = resposta.json()
            linhas.append({
                "repo": repo,
                "run_id": run_id,
                "tentativa": int(item.get("run_attempt") or k),
                "conclusion": item.get("conclusion"),
                "inicio": item.get("run_started_at"),
                "fim": item.get("updated_at"),
            })

    return linhas


def df_tentativas(linhas: list[dict]) -> pd.DataFrame:
    """DataFrame no contrato de run_attempts.csv, validado antes de sair."""
    df = pd.DataFrame(linhas, columns=list(SCHEMAS["run_attempts"].colunas))
    validar(df, SCHEMAS["run_attempts"])
    return df
