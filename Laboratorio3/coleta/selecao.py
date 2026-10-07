"""Geração dos candidatos: busca de repositórios por faixa de estrelas.

A busca devolve no máximo 1.000 resultados por consulta, então uma faixa que
chega a esse total é partida ao meio até cada pedaço caber. O que sai daqui
ainda tem duplicatas (as faixas do config se tocam nas pontas), forks e
arquivados: quem remove e registra cada descarte é `limpar_candidatos`, para
que o funil mostre o tamanho real de cada perda.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from coleta import http
from metricas.schemas import SCHEMAS, validar

BUSCA = "https://api.github.com/search/repositories"
TETO_POR_CONSULTA = 1000
# Faixa aberta (">50000") não tem meio para partir; este teto a fecha. Nenhum
# repositório do GitHub chega perto de um milhão de estrelas.
TETO_DE_ESTRELAS = 1_000_000

_RE_INTERVALO = re.compile(r"^(\d+)\.\.(\d+)$")
_RE_ABERTA = re.compile(r"^>\s*(\d+)$")

_log = logging.getLogger(__name__)


def intervalo_de(faixa: str) -> tuple[int, int]:
    """Faixa do config como (minimo, maximo), ambos inclusivos.

    `>50000` do config vira 50001..TETO, porque o operador exclui o 50000.
    """
    texto = faixa.strip()
    m = _RE_INTERVALO.match(texto)
    if m:
        minimo, maximo = int(m.group(1)), int(m.group(2))
    else:
        m = _RE_ABERTA.match(texto)
        if not m:
            raise ValueError(
                f"faixa de estrelas inválida: {faixa!r}. Use 'A..B' ou '>N'."
            )
        minimo, maximo = int(m.group(1)) + 1, TETO_DE_ESTRELAS
    if maximo < minimo:
        raise ValueError(f"faixa de estrelas invertida: {faixa!r}")
    return minimo, maximo


def _consulta(minimo: int, maximo: int) -> str:
    return f"stars:{minimo}..{maximo}"


def buscar_faixa(minimo: int, maximo: int) -> list[dict]:
    """Todos os repositórios da faixa, partindo-a quando satura.

    A primeira página da sondagem é a mesma que seria coletada de qualquer
    jeito, então no caminho normal nenhuma chamada é desperdiçada (e a de uma
    faixa partida vira acerto de cache se ela for repetida).
    """
    params = {
        "q": _consulta(minimo, maximo),
        "sort": "stars",
        "order": "desc",
        "per_page": 100,
    }
    primeira = http.get(BUSCA, params)
    carga = primeira.json()
    if "total_count" not in carga:
        raise KeyError(
            f"resposta de {BUSCA} sem 'total_count'; sem ele não dá para "
            f"saber se a faixa {minimo}..{maximo} saturou"
        )
    total = int(carga["total_count"])

    if total == 0:
        return []

    if total >= TETO_POR_CONSULTA:
        if minimo < maximo:
            meio = (minimo + maximo) // 2
            return buscar_faixa(minimo, meio) + buscar_faixa(meio + 1, maximo)
        # Uma contagem de estrelas só, e ainda assim ≥ 1.000 repositórios:
        # a API entrega os 1.000 primeiros e o resto fica de fora.
        _log.warning(
            "faixa %s..%s saturou (%s repositórios) e não dá para partir "
            "mais; só os 1.000 primeiros entram.", minimo, maximo, total,
        )

    itens = list(carga["items"])
    proximo = http.links(primeira.cabecalhos).get("next")
    visitadas: set[str] = set()
    while proximo and proximo not in visitadas:
        visitadas.add(proximo)
        pagina = http.get(proximo)
        itens.extend(pagina.json()["items"])
        proximo = http.links(pagina.cabecalhos).get("next")
    return itens


def buscar_candidatos(faixas: list[str]) -> list[dict]:
    """Itens brutos da busca, na ordem das faixas, com a faixa de origem.

    Cada item ganha `_faixa`. Duplicatas ficam: as faixas do config se tocam
    nas pontas (2000 está em duas), e contar quantas houve é papel do funil.
    """
    brutos: list[dict] = []
    for faixa in faixas:
        minimo, maximo = intervalo_de(faixa)
        for item in buscar_faixa(minimo, maximo):
            brutos.append({**item, "_faixa": faixa})
    return brutos


def _ultimo_push(item: dict) -> datetime | None:
    texto = item.get("pushed_at")
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def limpar_candidatos(
    brutos: list[dict],
    janela_inicio: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Remove duplicatas, forks, arquivados e, com `janela_inicio`, os parados.

    "Parado" é sem push desde o início da janela: ele não pode ter ≥ min_runs
    runs de push na janela, então seria descartado na etapa de runs de
    qualquer jeito. Cortar aqui só poupa chamadas (o `pushed_at` já vem na
    busca) e não muda quem pode entrar na amostra. Candidato sem `pushed_at`
    fica: na dúvida, quem decide é o filtro de verdade.

    Devolve (candidatos, descartes, etapas). `etapas` são as linhas do funil
    dessa fase, na ordem em que os filtros agem, de modo que a saída de uma é
    a entrada da próxima.

    Um repositório que é fork e também aparece duas vezes cai só em
    "duplicata": cada repositório sai uma vez, no primeiro filtro que o pega.
    """
    vistos: set[str] = set()
    descartes: list[dict] = []
    restantes: list[dict] = []

    for item in brutos:
        nome = item["full_name"]
        if nome in vistos:
            descartes.append({
                "repo": nome, "etapa": "duplicata",
                "motivo": "já veio de outra faixa de estrelas",
            })
            continue
        vistos.add(nome)
        restantes.append(item)

    etapas = [_etapa("duplicata", len(brutos), len(brutos) - len(restantes),
                     "já veio de outra faixa de estrelas")]

    for etapa, campo, motivo in (
        ("fork", "fork", "é um fork"),
        ("arquivado", "archived", "está arquivado"),
    ):
        entraram = len(restantes)
        mantidos = []
        for item in restantes:
            if item.get(campo):
                descartes.append({
                    "repo": item["full_name"], "etapa": etapa, "motivo": motivo,
                })
            else:
                mantidos.append(item)
        restantes = mantidos
        etapas.append(_etapa(etapa, entraram, entraram - len(restantes), motivo))

    if janela_inicio is not None:
        corte = datetime(janela_inicio.year, janela_inicio.month,
                         janela_inicio.day, tzinfo=timezone.utc)
        motivo = (f"sem push desde {janela_inicio.isoformat()}: não pode ter "
                  f"runs de push na janela")
        entraram = len(restantes)
        mantidos = []
        for item in restantes:
            push = _ultimo_push(item)
            if push is not None and push < corte:
                descartes.append({"repo": item["full_name"],
                                  "etapa": "sem_push_na_janela", "motivo": motivo})
            else:
                mantidos.append(item)
        restantes = mantidos
        etapas.append(_etapa("sem_push_na_janela", entraram,
                             entraram - len(restantes), motivo))

    candidatos = pd.DataFrame(
        [
            {
                "repo": i["full_name"],
                "estrelas": int(i["stargazers_count"]),
                "faixa_estrelas": i["_faixa"],
            }
            for i in restantes
        ],
        columns=list(SCHEMAS["candidatos"].colunas),
    )
    validar(candidatos, SCHEMAS["candidatos"])

    return (
        candidatos,
        pd.DataFrame(descartes, columns=list(SCHEMAS["descartes"].colunas)),
        etapas,
    )


def _etapa(etapa: str, entraram: int, sairam: int, motivo: str) -> dict:
    return {"etapa": etapa, "entraram": entraram, "sairam": sairam, "motivo": motivo}


def selecionar(cfg, pasta: str | Path = "data/processed") -> pd.DataFrame:
    """Do config à amostra: grava candidatos.csv, funil.csv e descartes.csv.

    Os filtros examinam os candidatos em ordem aleatória (pela semente) e
    param ao aprovar `cfg.n_repos`; os que sobram viram a linha
    `nao_examinados` do funil e não vão para descartes.csv (estão em
    candidatos.csv). Devolve a amostra com as colunas de candidatos.csv.
    """
    from coleta.filtros import df_descartes, df_funil, filtrar_ate, funil_fecha

    candidatos, desc_limpeza, etapas = limpar_candidatos(
        buscar_candidatos(cfg.faixas_estrelas), cfg.janela_inicio
    )
    aprovados, desc_filtros, funil_filtros, nao_examinados = filtrar_ate(
        candidatos["repo"].tolist(), cfg, cfg.n_repos, cfg.seed
    )
    motivo = (f"não examinados: a amostra de {cfg.n_repos} fechou antes "
              f"(ordem aleatória, seed={cfg.seed})")
    etapa_nao_examinados = _etapa("nao_examinados", len(candidatos),
                                  nao_examinados, motivo)

    funil = df_funil(etapas + [etapa_nao_examinados] + funil_filtros)
    if not funil_fecha(funil, len(aprovados)):
        raise RuntimeError("o funil não fecha: confira funil.csv antes de seguir")
    descartes = df_descartes(desc_limpeza.to_dict("records") + desc_filtros)

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    candidatos.to_csv(pasta / "candidatos.csv", index=False)
    funil.to_csv(pasta / "funil.csv", index=False)
    descartes.to_csv(pasta / "descartes.csv", index=False)
    return candidatos[candidatos["repo"].isin(aprovados)].reset_index(drop=True)
