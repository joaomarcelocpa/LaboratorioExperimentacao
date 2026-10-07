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


def limpar_candidatos(
    brutos: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Remove duplicatas, forks e arquivados.

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

    Devolve a amostra sorteada com as colunas de candidatos.csv.
    """
    from coleta.filtros import df_descartes, df_funil, filtrar, funil_fecha, sortear

    candidatos, desc_limpeza, etapas = limpar_candidatos(
        buscar_candidatos(cfg.faixas_estrelas)
    )
    aprovados, desc_filtros, funil_filtros = filtrar(candidatos["repo"].tolist(), cfg)
    amostra, desc_sorteio, etapa_sorteio = sortear(aprovados, cfg.n_repos, cfg.seed)

    funil = df_funil(etapas + funil_filtros + [etapa_sorteio])
    if not funil_fecha(funil, len(amostra)):
        raise RuntimeError("o funil não fecha: confira funil.csv antes de seguir")
    descartes = df_descartes(
        desc_limpeza.to_dict("records") + desc_filtros + desc_sorteio
    )

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    candidatos.to_csv(pasta / "candidatos.csv", index=False)
    funil.to_csv(pasta / "funil.csv", index=False)
    descartes.to_csv(pasta / "descartes.csv", index=False)
    return candidatos[candidatos["repo"].isin(amostra)].reset_index(drop=True)
