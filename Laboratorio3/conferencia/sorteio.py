"""Sorteio da amostra-ouro e geração da planilha de conferência manual.

Uso: python -m conferencia.sorteio [--config config.yaml] [--saida data/conferencia]

Sorteia 60 repositórios da amostra final e, em cada um, 5 releases. A seed é a
do config.yaml: a mesma seed e os mesmos CSVs geram sempre a mesma amostra.
A planilha NÃO mostra o que a heurística automática achou, para não influenciar
quem rotula.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from pipeline.config import carregar_config

N_REPOS = 60
N_RELEASES = 5
MAX_COMMITS = 40
MAX_NOTAS = 1500
MAX_MENSAGEM = 160

COLUNAS_PLANILHA_REPOS = [
    "repo", "link", "linguagem", "estrelas", "tipo_projeto", "entregas_reais",
]
COLUNAS_PLANILHA_RELEASES = [
    "repo", "tag", "link", "publicada_em", "notas", "commits", "corretiva",
]


def abrir_csv(caminho: Path):
    """Abre um CSV puro ou um .zip com um CSV dentro (ignora o lixo __MACOSX)."""
    caminho = Path(caminho)
    if caminho.suffix != ".zip":
        return caminho
    zf = zipfile.ZipFile(caminho)
    nomes = [n for n in zf.namelist()
             if not n.startswith("__MACOSX") and n.endswith(".csv")]
    if len(nomes) != 1:
        raise ValueError(f"esperava 1 CSV em {caminho}, achei {nomes}")
    return zf.open(nomes[0])


def localizar_csv(pasta: Path, nome: str) -> Path:
    """Aceita nome.csv ou nome.csv.zip (os dois grandes foram zipados)."""
    for candidato in (pasta / nome, pasta / f"{nome}.zip"):
        if candidato.exists():
            return candidato
    raise FileNotFoundError(f"{nome} nem {nome}.zip em {pasta}")


def link_release(repo: str, tag: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}"


def pares_com_commits(caminho: Path) -> set[tuple[str, str]]:
    """(repo, release_tag) que têm ao menos um commit no intervalo."""
    pares: set[tuple[str, str]] = set()
    leitor = pd.read_csv(
        abrir_csv(caminho), usecols=["repo", "release_tag"],
        dtype=str, chunksize=500_000,
    )
    for pedaco in leitor:
        pares.update(zip(pedaco["repo"], pedaco["release_tag"]))
    return pares


def mensagens_das_releases(
    caminho: Path, escolhidas: set[tuple[str, str]],
) -> dict[tuple[str, str], list[str]]:
    """Primeira linha da mensagem dos commits, só das releases sorteadas."""
    saida: dict[tuple[str, str], list[str]] = {p: [] for p in escolhidas}
    leitor = pd.read_csv(
        abrir_csv(caminho), usecols=["repo", "release_tag", "mensagem"],
        dtype=str, keep_default_na=False, chunksize=500_000,
    )
    for pedaco in leitor:
        for repo, tag, msg in zip(
            pedaco["repo"], pedaco["release_tag"], pedaco["mensagem"]
        ):
            if (repo, tag) in saida:
                saida[(repo, tag)].append(msg.split("\n", 1)[0].strip())
    return saida


def sortear_repos(repos: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    base = repos.sort_values("repo").reset_index(drop=True)
    if len(base) < n:
        raise ValueError(f"só há {len(base)} repositórios, pedi {n}")
    return base.sample(n=n, random_state=seed).sort_values("repo").reset_index(drop=True)


def sortear_releases(
    releases: pd.DataFrame,
    repos_sorteados: list[str],
    elegiveis: set[tuple[str, str]],
    n: int,
    seed: int,
) -> pd.DataFrame:
    """Até n releases por repo: dentro da janela, não pré-release, com commits."""
    r = releases[releases["na_janela"] & ~releases["prerelease"]]
    r = r[r["repo"].isin(repos_sorteados)]
    r = r[[(a, b) in elegiveis for a, b in zip(r["repo"], r["tag"])]]
    r = r.sort_values(["repo", "publicada_em", "tag"]).reset_index(drop=True)
    partes = []
    for repo, grupo in r.groupby("repo", sort=True):
        if len(grupo) < n:
            print(f"aviso: {repo} tem só {len(grupo)} releases elegíveis", file=sys.stderr)
        partes.append(grupo.sample(n=min(n, len(grupo)), random_state=seed))
    if not partes:
        return r.iloc[0:0]
    return pd.concat(partes).sort_values(["repo", "publicada_em", "tag"]).reset_index(drop=True)


def formatar_commits(mensagens: list[str]) -> str:
    linhas = [f"- {m[:MAX_MENSAGEM]}" for m in mensagens[:MAX_COMMITS]]
    resto = len(mensagens) - MAX_COMMITS
    if resto > 0:
        linhas.append(f"(e mais {resto} commits)")
    return "\n".join(linhas)


def montar_planilhas(
    repos: pd.DataFrame,
    releases: pd.DataFrame,
    mensagens: dict[tuple[str, str], list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    p_repos = pd.DataFrame({
        "repo": repos["repo"],
        "link": [f"https://github.com/{r}" for r in repos["repo"]],
        "linguagem": repos["linguagem"],
        "estrelas": repos["estrelas"],
        "tipo_projeto": "",
        "entregas_reais": "",
    })[COLUNAS_PLANILHA_REPOS]

    notas = releases["body"].fillna("").astype(str).str.slice(0, MAX_NOTAS)
    p_rel = pd.DataFrame({
        "repo": releases["repo"],
        "tag": releases["tag"],
        "link": [link_release(a, b) for a, b in zip(releases["repo"], releases["tag"])],
        "publicada_em": releases["publicada_em"],
        "notas": notas,
        "commits": [
            formatar_commits(mensagens.get((a, b), []))
            for a, b in zip(releases["repo"], releases["tag"])
        ],
        "corretiva": "",
    })[COLUNAS_PLANILHA_RELEASES]
    return p_repos, p_rel


def gerar(
    processed: Path, saida: Path, seed: int, n_repos: int = N_REPOS,
) -> dict[str, Path]:
    repos = pd.read_csv(processed / "repos.csv")
    releases = pd.read_csv(processed / "releases.csv")
    caminho_commits = localizar_csv(processed, "commits.csv")

    sorteados = sortear_repos(repos, n_repos, seed)
    elegiveis = pares_com_commits(caminho_commits)
    sorteadas = sortear_releases(
        releases, list(sorteados["repo"]), elegiveis, N_RELEASES, seed,
    )
    escolhidas = set(zip(sorteadas["repo"], sorteadas["tag"]))
    mensagens = mensagens_das_releases(caminho_commits, escolhidas)
    p_repos, p_rel = montar_planilhas(sorteados, sorteadas, mensagens)

    saida.mkdir(parents=True, exist_ok=True)
    arquivos = {
        "amostra_ouro": saida / "amostra_ouro.csv",
        "planilha_repositorios": saida / "planilha_repositorios.csv",
        "planilha_releases": saida / "planilha_releases.csv",
    }
    sorteadas[["repo", "tag"]].to_csv(arquivos["amostra_ouro"], index=False)
    # utf-8-sig: o Excel abre acentos e emojis corretamente
    p_repos.to_csv(arquivos["planilha_repositorios"], index=False, encoding="utf-8-sig")
    p_rel.to_csv(arquivos["planilha_releases"], index=False, encoding="utf-8-sig")
    return arquivos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conferencia.sorteio")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--saida", default="data/conferencia")
    args = parser.parse_args(argv)
    cfg = carregar_config(args.config)
    arquivos = gerar(Path(args.processed), Path(args.saida), cfg.seed)
    print(f"seed {cfg.seed}: {N_REPOS} repositórios, {N_RELEASES} releases cada")
    for nome, caminho in arquivos.items():
        print(f"  {nome}: {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
