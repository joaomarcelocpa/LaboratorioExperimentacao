"""Visão só de releases estáveis, para a definição principal de deploy.

O enunciado (seção 3) define deploy como release publicada sem pré-release;
as pré-releases são variante da RQ 07. A coleta, porém, encadeia todas as
releases (estáveis e pré-releases) para pedir os commits de cada intervalo,
e isso é o certo: cobre toda a história sem buracos.

Quem calcula as métricas principais precisa da cadeia só de estáveis. Em vez
de recoletar, esta visão a reconstrói: tira as pré-releases da lista e passa
os commits de cada pré-release para a PRÓXIMA release estável, que é a que de
fato os entrega. Sem isso, o lead time de uma release perderia os commits que
já tinham aparecido numa pré-release dela, e uma pré-release de patch
contaria como release corretiva no CFR (b).
"""
from __future__ import annotations

import pandas as pd


def visao_estavel(
    releases: pd.DataFrame, commits: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(releases estáveis, commits reatribuídos à release estável que os entrega).

    Commits de pré-releases publicadas depois da última estável ficam de fora:
    ainda não foram entregues por nenhuma release estável.
    """
    if releases.empty or "prerelease" not in releases.columns:
        return releases, commits

    eh_pre = releases["prerelease"].astype(bool)
    estaveis = releases[~eh_pre].sort_values("publicada_em")
    if commits.empty or "release_tag" not in commits.columns:
        return estaveis, commits

    # ISO 8601 em UTC ordena como texto, o mesmo que o resto das métricas faz.
    publicadas = list(estaveis[["publicada_em", "tag"]].itertuples(index=False, name=None))
    destino: dict[str, str | None] = {tag: tag for _, tag in publicadas}
    for _, pre in releases[eh_pre].iterrows():
        destino[pre["tag"]] = next(
            (tag for quando, tag in publicadas if quando > pre["publicada_em"]), None
        )

    novos = commits.copy()
    novos["release_tag"] = novos["release_tag"].map(lambda t: destino.get(t, t))
    return estaveis, novos[novos["release_tag"].notna()].reset_index(drop=True)
