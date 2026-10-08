from pathlib import Path

import pytest

from metricas.schemas import SCHEMAS

README = Path("README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("schema", SCHEMAS.values(), ids=lambda s: s.nome)
def test_readme_documenta_cada_csv_do_contrato(schema):
    assert schema.nome in README


@pytest.mark.parametrize("trecho", [
    "python -m pipeline --config config.yaml",
    "--limite",
    "GITHUB_TOKEN",
    "make run-docker",
    "python -m pipeline.estimativa",
    "fatias_saturadas.csv",
    "custo_selecao.csv",
    "sem_push_na_janela",
    "nao_examinados",
    "checkpoint",
    "403, 422 e 410",
])
def test_readme_traz_o_essencial(trecho):
    assert trecho in README
