"""Monta data/raw/prs.csv: amostra de PRs mesclados do AIDev, com e sem bot de revisao.

Uso:
    python src/coletar_dados.py <pasta com pull_request.parquet e pr_reviews.parquet>

Fonte: https://huggingface.co/datasets/hao-li/AIDev (CC-BY-4.0).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AGENTE = "Claude_Code"
N_POR_GRUPO = 30
SEMENTE = 42
BOTS_REVISORES = {
    "copilot-pull-request-reviewer[bot]",
    "coderabbitai[bot]",
    "gemini-code-assist[bot]",
    "greptile-apps[bot]",
    "cubic-dev-ai[bot]",
}
SAIDA = Path(__file__).resolve().parent.parent / "data" / "raw" / "prs.csv"


def main(pasta: Path) -> None:
    pr = pd.read_parquet(
        pasta / "pull_request.parquet",
        columns=["id", "agent", "created_at", "merged_at", "repo_url", "html_url"],
    )
    rv = pd.read_parquet(
        pasta / "pr_reviews.parquet",
        columns=["pr_id", "user", "user_type", "submitted_at"],
    )

    pr = pr[(pr.agent == AGENTE) & pr.merged_at.notna()].copy()
    pr["criado"] = pd.to_datetime(pr.created_at, utc=True)
    pr["mesclado"] = pd.to_datetime(pr.merged_at, utc=True)
    pr["horas_ate_merge"] = (pr.mesclado - pr.criado).dt.total_seconds() / 3600
    pr = pr[pr.horas_ate_merge > 0]

    # So conta revisao feita antes do merge.
    rv["enviado"] = pd.to_datetime(rv.submitted_at, utc=True)
    rv = rv.merge(pr[["id", "mesclado"]], left_on="pr_id", right_on="id")
    rv = rv[rv.enviado <= rv.mesclado]

    com_bot = rv[rv.user.isin(BOTS_REVISORES)].groupby("pr_id").user.first()
    com_humano = set(rv[rv.user_type == "User"].pr_id)

    pr["revisor_bot"] = pr.id.map(com_bot)
    pr["grupo"] = np.where(
        pr.revisor_bot.notna(),
        "com_bot",
        np.where(pr.id.isin(com_humano), "sem_bot", "descartar"),
    )
    pr = pr[pr.grupo != "descartar"]

    rng = np.random.default_rng(SEMENTE)
    amostra = pd.concat(
        g.sample(n=N_POR_GRUPO, random_state=int(rng.integers(1_000_000)))
        for _, g in pr.groupby("grupo")
    )
    amostra["repositorio"] = amostra.repo_url.str.replace(
        "https://api.github.com/repos/", "", regex=False
    )
    saida = amostra[
        ["id", "grupo", "agent", "repositorio", "html_url",
         "created_at", "merged_at", "horas_ate_merge", "revisor_bot"]
    ].rename(columns={"id": "pr_id", "agent": "agente", "html_url": "url"})
    saida["horas_ate_merge"] = saida.horas_ate_merge.round(2)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    saida.sort_values(["grupo", "pr_id"]).to_csv(SAIDA, index=False)
    print(f"{len(saida)} PRs salvos em {SAIDA}")
    print(saida.groupby("grupo").horas_ate_merge.describe().round(1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
