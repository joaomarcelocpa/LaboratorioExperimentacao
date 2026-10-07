"""Garante que o esqueleto do projeto existe e é importável."""
import importlib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("pacote", ["pipeline", "coleta", "metricas"])
def test_pacote_e_importavel(pacote):
    assert importlib.import_module(pacote) is not None


@pytest.mark.parametrize(
    "caminho",
    [
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "data/raw/.gitkeep",
        "data/processed/.gitkeep",
    ],
)
def test_arquivo_existe(caminho):
    assert (RAIZ / caminho).exists(), f"{caminho} não foi criado"


def test_env_example_nao_tem_token_real():
    conteudo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    assert "GITHUB_TOKEN=" in conteudo
    linha = [l for l in conteudo.splitlines() if l.startswith("GITHUB_TOKEN=")][0]
    assert linha.strip() == "GITHUB_TOKEN=", "o exemplo não pode conter um token real"


def test_gitignore_protege_segredos_e_cache():
    conteudo = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    for padrao in [".env", "data/raw/", ".venv/", "__pycache__/"]:
        assert padrao in conteudo, f"{padrao} faltando no .gitignore"
