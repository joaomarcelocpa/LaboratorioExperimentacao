from analise_estatistica import (
    _mediana_iqr,
    _pares_por_kata,
    _wilcoxon_pareado,
    analisar_halstead,
    analisar_rq1,
    analisar_rq2,
    analisar_rq3,
)
from consolidar_dados import carregar_trials


def test_mediana_iqr():
    resultado = _mediana_iqr([1, 2, 3, 4])
    assert resultado["mediana"] == 2.5
    assert resultado["n"] == 4


def test_pares_por_kata_alinha_manual_e_ia_pela_mesma_kata():
    linhas = [
        {"kata_id": "F1", "tratamento": "manual", "tempo_segundos": 100},
        {"kata_id": "F1", "tratamento": "ia", "tempo_segundos": 10},
        {"kata_id": "F2", "tratamento": "manual", "tempo_segundos": 200},
        {"kata_id": "F2", "tratamento": "ia", "tempo_segundos": 20},
    ]
    manual, ia = _pares_por_kata(linhas, "tempo_segundos")
    assert manual == [100, 200]
    assert ia == [10, 20]


def test_wilcoxon_nao_aplicavel_quando_todas_diferencas_sao_zero():
    resultado = _wilcoxon_pareado([1, 2, 3], [1, 2, 3])
    assert resultado["aplicavel"] is False


def test_wilcoxon_aplicavel_com_diferencas():
    resultado = _wilcoxon_pareado([100, 200, 300, 400, 500, 600], [10, 20, 30, 40, 50, 60])
    assert resultado["aplicavel"] is True
    assert "p_valor" in resultado


def test_analisar_rq1_ia_mais_rapida_que_manual_nos_dados_reais():
    linhas = carregar_trials()
    resultado = analisar_rq1(linhas)
    assert resultado["ia"]["mediana"] < resultado["manual"]["mediana"]
    assert resultado["wilcoxon_pareado_por_kata"]["aplicavel"] is True


def test_analisar_rq2_sem_variacao_nos_dados_reais():
    linhas = carregar_trials()
    resultado = analisar_rq2(linhas)
    assert resultado["manual"]["mediana"] == 100.0
    assert resultado["ia"]["mediana"] == 100.0
    assert resultado["wilcoxon_pareado_por_kata"]["aplicavel"] is False


def test_analisar_rq3_cobre_as_quatro_metricas_e_a_normalizada():
    linhas = carregar_trials()
    resultado = analisar_rq3(linhas)

    for campo in ("cc_media", "mi", "loc", "duplicacao_pct", "cc_normalizada_por_100_loc"):
        assert campo in resultado
        assert resultado[campo]["manual"]["n"] == 6
        assert resultado[campo]["ia"]["n"] == 6


def test_duplicacao_sem_variacao_nos_dados_reais():
    linhas = carregar_trials()
    resultado = analisar_rq3(linhas)
    assert resultado["duplicacao_pct"]["manual"]["mediana"] == 0.0
    assert resultado["duplicacao_pct"]["wilcoxon_pareado_por_kata"]["aplicavel"] is False


def test_analisar_halstead_ia_tem_esforco_menor_nos_dados_reais():
    linhas = carregar_trials()
    resultado = analisar_halstead(linhas)
    assert resultado["hal_esforco"]["ia"]["mediana"] < resultado["hal_esforco"]["manual"]["mediana"]
    assert resultado["hal_esforco"]["wilcoxon_pareado_por_kata"]["aplicavel"] is True
