"""Contrato do carregador de configuração."""
from datetime import date
from pathlib import Path

import pytest

from pipeline.config import ErroDeConfig, carregar_config

RAIZ = Path(__file__).resolve().parent.parent


def escrever(tmp_path: Path, texto: str) -> Path:
    caminho = tmp_path / "config.yaml"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


VALIDO = """
janela: {inicio: 2024-10-01, fim: 2025-09-30, placeholder: false}
faixas_estrelas: ["1000..2000"]
min_releases: 5
min_runs: 50
n_repos: 100
seed: 42
ambientes_producao: [production]
labels_bug: [bug]
n_dias_issue: 7
bots: ["dependabot[bot]"]
"""


def test_config_do_repositorio_carrega():
    cfg = carregar_config(RAIZ / "config.yaml")
    assert cfg.min_releases == 5
    assert cfg.min_runs == 50
    assert cfg.n_repos == 100
    assert cfg.seed == 42
    assert cfg.n_dias_issue == 7
    assert "dependabot[bot]" in cfg.bots


def test_config_valido_tem_tipos_certos(tmp_path):
    cfg = carregar_config(escrever(tmp_path, VALIDO))
    assert cfg.janela_inicio == date(2024, 10, 1)
    assert cfg.janela_fim == date(2025, 9, 30)
    assert isinstance(cfg.faixas_estrelas, list)
    assert isinstance(cfg.min_releases, int)


def test_arquivo_inexistente_da_erro_claro(tmp_path):
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(tmp_path / "nao_existe.yaml")
    assert "nao_existe.yaml" in str(e.value)


def test_yaml_malformado_da_erro_claro(tmp_path):
    caminho = escrever(tmp_path, "janela: {inicio: 2024-01-01\nmin_releases: 5")
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(caminho)
    assert "YAML inválido" in str(e.value)


@pytest.mark.parametrize("texto", ["", "null", "- um\n- dois"])
def test_yaml_que_nao_e_mapa_da_erro_claro(tmp_path, texto):
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(escrever(tmp_path, texto))
    assert "mapa" in str(e.value)


def test_chave_ausente_nomeia_a_chave(tmp_path):
    sem_seed = VALIDO.replace("seed: 42\n", "")
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(escrever(tmp_path, sem_seed))
    assert "seed" in str(e.value)


def test_tipo_errado_nomeia_a_chave(tmp_path):
    texto = VALIDO.replace("min_releases: 5", 'min_releases: "cinco"')
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(escrever(tmp_path, texto))
    msg = str(e.value)
    assert "min_releases" in msg and "int" in msg


def test_janela_invertida_da_erro(tmp_path):
    texto = VALIDO.replace("fim: 2025-09-30", "fim: 2024-01-01")
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(escrever(tmp_path, texto))
    assert "anterior" in str(e.value)


def test_janela_placeholder_e_detectada(tmp_path):
    texto = VALIDO.replace("placeholder: false", "placeholder: true")
    assert carregar_config(escrever(tmp_path, texto)).janela_e_placeholder() is True
    assert carregar_config(escrever(tmp_path, VALIDO)).janela_e_placeholder() is False


def test_config_do_repositorio_ainda_e_placeholder():
    # Quando o professor divulgar a janela, apague placeholder e este teste.
    cfg = carregar_config(RAIZ / "config.yaml")
    assert cfg.janela_e_placeholder() is True


def test_pipeline_recusa_rodar_com_janela_placeholder(capsys):
    from pipeline.__main__ import main

    codigo = main(["--config", str(RAIZ / "config.yaml")])
    assert codigo == 2
    assert "placeholder" in capsys.readouterr().err


# --- correções da revisão final ---

def test_janela_com_hora_da_erro_claro(tmp_path):
    """datetime é subclasse de date: sem checagem explícita, a comparação
    datetime vs date estoura TypeError em vez de ErroDeConfig."""
    texto = VALIDO.replace("inicio: 2024-10-01", "inicio: 2024-10-01 00:00:00")
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(escrever(tmp_path, texto))
    assert "janela.inicio" in str(e.value)


def test_config_que_e_diretorio_da_erro_claro(tmp_path):
    with pytest.raises(ErroDeConfig) as e:
        carregar_config(tmp_path)
    assert str(tmp_path) in str(e.value)
