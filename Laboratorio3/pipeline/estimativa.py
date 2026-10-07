"""Estimativa de custo e tempo de uma coleta maior, a partir de uma menor.

Extrapolação linear: assume que cada repositório custa o mesmo. É uma
aproximação — repositórios gigantes e o custo fixo da seleção distorcem —
então vale como ordem de grandeza para planejar a rodada de 300, não como
promessa.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

COTA_POR_HORA = 5000


def estimar(
    custo: pd.DataFrame,
    n_medido: int,
    n_alvo: int,
    segundos: float,
    cota_hora: int = COTA_POR_HORA,
    custo_selecao: pd.DataFrame | None = None,
    segundos_selecao: float = 0.0,
) -> dict:
    """Projeta chamadas e horas para `n_alvo` repositórios.

    `horas_por_tempo` extrapola o relógio medido; `horas_por_cota` é o piso
    imposto pela cota da API. O que vale é o maior dos dois.

    A seleção (busca e filtros) percorre todos os candidatos, não só a
    amostra, então seu custo é fixo: com `custo_selecao` e `segundos_selecao`
    ela é separada do custo por repositório e somada uma vez só no alvo.
    Sem eles, a seleção é diluída nos repositórios e a estimativa sai inflada.
    """
    if n_medido < 1:
        raise ValueError("n_medido deve ser >= 1")
    total = int(custo["chamadas"].sum())
    fixas = int(custo_selecao["chamadas"].sum()) if custo_selecao is not None else 0
    por_repo = (total - fixas) / n_medido
    alvo = por_repo * n_alvo + fixas
    por_tempo = ((segundos - segundos_selecao) / n_medido * n_alvo
                 + segundos_selecao) / 3600
    por_cota = alvo / cota_hora
    mais_caro = (custo.loc[custo["chamadas"].idxmax(), "endpoint"]
                 if total > 0 else None)
    return {
        "chamadas_por_repo": por_repo,
        "chamadas_alvo": round(alvo),
        "horas_por_tempo": por_tempo,
        "horas_por_cota": por_cota,
        "horas_estimadas": max(por_tempo, por_cota),
        "endpoint_mais_caro": mais_caro,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pipeline.estimativa")
    p.add_argument("--custo", default="data/processed/custo_api.csv")
    p.add_argument("--medido", type=int, required=True, help="repositórios da rodada medida")
    p.add_argument("--segundos", type=float, required=True, help="tempo da rodada medida")
    p.add_argument("--alvo", type=int, default=300)
    p.add_argument("--selecao", default="data/processed/custo_selecao.csv",
                   help="custo só da seleção (fixo); ignorado se o arquivo não existir")
    p.add_argument("--segundos-selecao", type=float, default=0.0,
                   help="tempo da seleção, impresso no fim da rodada medida")
    a = p.parse_args(argv)
    sel = pd.read_csv(a.selecao) if Path(a.selecao).exists() else None
    r = estimar(pd.read_csv(a.custo), a.medido, a.alvo, a.segundos,
                custo_selecao=sel, segundos_selecao=a.segundos_selecao)
    print(f"{r['chamadas_por_repo']:.0f} chamadas/repo → {r['chamadas_alvo']} para {a.alvo} repos")
    print(f"≈ {r['horas_estimadas']:.1f} h (tempo {r['horas_por_tempo']:.1f} h, "
          f"cota {r['horas_por_cota']:.1f} h); mais caro: {r['endpoint_mais_caro']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
