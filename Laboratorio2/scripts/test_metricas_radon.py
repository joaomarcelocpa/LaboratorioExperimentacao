from pathlib import Path

from metricas_radon import _analisar_arquivo

EXEMPLO = Path(__file__).parent / "sample" / "exemplo.py"


def test_analisar_arquivo_inclui_metricas_halstead():
    resultado = _analisar_arquivo(EXEMPLO)
    assert "hal" in resultado
    assert set(resultado["hal"]["total"].keys()) == {
        "volume",
        "dificuldade",
        "esforco",
        "bugs_estimados",
        "tempo_estimado_seg",
    }
    assert resultado["hal"]["total"]["volume"] > 0
    assert resultado["hal"]["total"]["esforco"] > 0


def test_halstead_por_funcao_cobre_todas_as_funcoes_e_metodos():
    resultado = _analisar_arquivo(EXEMPLO)
    nomes = {f["nome"] for f in resultado["hal"]["por_funcao"]}
    assert nomes == {
        "soma",
        "classifica_nota",
        "fatorial",
        "busca_binaria",
        "__init__",
        "calcular",
    }


def test_halstead_por_funcao_tem_metricas_numericas():
    resultado = _analisar_arquivo(EXEMPLO)
    fatorial = next(f for f in resultado["hal"]["por_funcao"] if f["nome"] == "fatorial")
    assert fatorial["volume"] > 0
    assert fatorial["dificuldade"] > 0
    assert fatorial["esforco"] > 0
    assert fatorial["bugs_estimados"] >= 0
