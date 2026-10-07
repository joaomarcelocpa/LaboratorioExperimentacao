"""O ambiente reprodutível é parte do aceite: outro integrante roda
`make run-docker` em máquina limpa seguindo só o README."""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _raiz_do_git() -> Path | None:
    for pasta in [RAIZ, *RAIZ.parents]:
        if (pasta / ".git").exists():
            return pasta
    return None


@pytest.fixture
def workflow() -> str:
    # O workflow mora na raiz do monorepo, não em Laboratorio3.
    raiz = _raiz_do_git()
    if raiz is None:
        pytest.skip("sem .git: cópia da pasta sem histórico, não é defeito do pipeline")
    caminho = raiz / ".github" / "workflows" / "testes.yml"
    if not caminho.exists():
        pytest.fail(f"workflow não encontrado em {caminho}")
    return caminho.read_text(encoding="utf-8")


@pytest.fixture
def makefile() -> str:
    return (RAIZ / "Makefile").read_text(encoding="utf-8")


@pytest.fixture
def dockerfile() -> str:
    return (RAIZ / "Dockerfile").read_text(encoding="utf-8")


# --- CI -----------------------------------------------------------------

def test_workflow_cobre_a_cobertura_minima(workflow):
    assert "--cov-fail-under=80" in workflow


def test_workflow_mede_metricas_e_coleta(workflow):
    assert "--cov=metricas" in workflow
    assert "--cov=coleta" in workflow


def test_workflow_roda_dentro_do_laboratorio3(workflow):
    # O repositório tem Laboratorio1..5; sem isto o CI tentaria testar tudo.
    assert "working-directory: Laboratorio3" in workflow


def test_workflow_checa_o_contrato(workflow):
    assert "python -m metricas.dicionario" in workflow
    assert "git diff --exit-code docs/dicionario_dados.md" in workflow


def test_workflow_valida_o_dockerfile(workflow):
    # Não há docker na máquina de desenvolvimento: o CI é a verificação.
    assert "docker build" in workflow


def test_workflow_usa_python_312(workflow):
    assert '"3.12"' in workflow or "'3.12'" in workflow


# --- Docker -------------------------------------------------------------

def test_dockerfile_usa_python_312(dockerfile):
    assert "FROM python:3.12" in dockerfile


def test_dockerfile_instala_as_dependencias_fixas(dockerfile):
    assert "requirements.txt" in dockerfile


def test_dockerfile_expoe_volume_de_dados(dockerfile):
    # Sem o volume, o cache morre junto com o container e a retomada some.
    assert "/app/data" in dockerfile


def test_dockerfile_roda_o_pipeline(dockerfile):
    assert "pipeline" in dockerfile


def test_dockerignore_protege_segredos_e_cache():
    conteudo = (RAIZ / ".dockerignore").read_text(encoding="utf-8")
    for padrao in [".env", "data/raw", ".git"]:
        assert padrao in conteudo, f"{padrao} faltando no .dockerignore"


# --- Makefile -----------------------------------------------------------

@pytest.mark.parametrize("alvo", ["test", "run", "run-docker", "reproduce", "contrato"])
def test_makefile_tem_o_alvo(makefile, alvo):
    assert f"\n{alvo}:" in f"\n{makefile}", f"alvo {alvo} faltando"


def test_makefile_declara_os_alvos_como_phony(makefile):
    assert ".PHONY" in makefile


def test_makefile_usa_tab_nas_receitas(makefile):
    # Make exige tab literal; um editor que converte em espaços quebra tudo.
    receitas = [l for l in makefile.splitlines() if l.startswith("\t")]
    assert len(receitas) >= 6, "as receitas não estão indentadas com tab"


def test_run_docker_passa_o_token_e_monta_data(makefile):
    linha = [l for l in makefile.splitlines() if "docker run" in l][0]
    assert "GITHUB_TOKEN" in linha
    assert "/app/data" in linha


# --- README -------------------------------------------------------------

def test_readme_documenta_make_e_o_equivalente_sem_make():
    conteudo = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert "make run-docker" in conteudo
    assert "GITHUB_TOKEN" in conteudo
    # Nem esta máquina nem o Windows padrão têm make.
    assert "powershell" in conteudo.lower()
