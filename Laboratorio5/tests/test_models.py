import numpy as np
import pandas as pd
import pytest

from analysis import models
from analysis.synthetic import Parametros, gerar


@pytest.fixture(scope="module")
def df():
    return gerar(12, seed=7)


def test_cliffs_delta_extremos_e_empate():
    assert models.cliffs_delta([5, 6], [1, 2]) == 1.0
    assert models.cliffs_delta([1, 2], [5, 6]) == -1.0
    assert models.cliffs_delta([1, 2], [1, 2]) == 0.0


def test_holm_confere_com_calculo_manual():
    t = models.holm(pd.DataFrame({"p": [0.01, 0.04, 0.03]}))
    # ordenados: 0.01*3, 0.03*2, 0.04*1 com monotonicidade => 0.03, 0.06, 0.06
    assert t["p_holm"].tolist() == pytest.approx([0.03, 0.06, 0.06])
    assert t["rejeita_h0"].tolist() == [True, False, False]


def test_glmm_recupera_a_interacao_verdadeira():
    d = gerar(25, parametros=Parametros(inclinacao_extra_inc=0.15), seed=3)
    out = models.glmm_regressao(d).set_index("termo")
    assert out.loc["inc:step", "coef"] == pytest.approx(0.15, abs=0.05)
    assert out.loc["inc:step", "odds_ratio"] > 1


def test_glmm_sem_efeito_nao_acusa_interacao_grande():
    d = gerar(25, parametros=Parametros(inclinacao_extra_inc=0.0), seed=3)
    assert abs(models.glmm_regressao(d).set_index("termo").loc["inc:step", "coef"]) < 0.05


def test_gee_concorda_em_sinal_com_glmm(df):
    a = models.glmm_regressao(df).set_index("termo")["coef"]
    b = models.glmm_sensibilidade(df).set_index("termo")["coef"]
    assert np.sign(a["inc:step"]) == np.sign(b["inc:step"])


def test_curva_de_crescimento_acha_inclinacao_do_incremental(df):
    t = models.curva_de_crescimento(df, "dup_pct").set_index("termo")
    assert t.loc["inc:step", "coef"] > 0
    assert t.loc["inc:step", "p"] < 0.05


def test_diferenca_pareada_tem_um_passo_por_linha(df):
    r = models.diferenca_pareada(df)
    assert r["passo"].tolist() == list(range(1, 11))
    assert (r["pares"] == 12).all()
    assert r["cliffs_delta"].between(-1, 1).all()


def test_h5_devolve_regressao_e_violacoes(df):
    r = models.efeito_tipo_de_pedido(df)
    assert len(r) == 2
    assert r.iloc[0]["odds_ratio"] > 1  # pedido que tensiona regride mais (efeito 0,5 no gerador)


def test_variancia_entre_cadeias_formato(df):
    v = models.variancia_entre_cadeias(df)
    assert {"mode", "step", "variancia", "cadeias"} <= set(v.columns)
    assert set(v.attrs["tendencia"]["mode"]) == {"incremental", "regenerado"}


def test_ordem_deduzida_do_pedido_do_passo_1(df):
    ordem = models.ordem_das_cadeias(df)
    assert set(ordem) == {"A", "B"}
    assert ordem.loc[(1, "incremental")] == "A" and ordem.loc[(2, "regenerado")] == "B"


def test_tipos_seguem_o_protocolo_congelado(df):
    tipos = df[df["step"] >= 1].groupby("request_id")["request_type"].first()
    assert sorted(tipos[tipos == "tensiona"].index) == ["P10", "P3", "P5", "P6", "P9"]


def test_glmm_com_covariaveis_mantem_a_interacao(df):
    cov = models.glmm_covariaveis(df).set_index("termo")
    assert {"rodou_testes", "ordem_b", "inc:step"} <= set(cov.index)
    base = models.glmm_regressao(df).set_index("termo")
    assert np.sign(cov.loc["inc:step", "coef"]) == np.sign(base.loc["inc:step", "coef"])


def test_glmm_sem_variacao_no_desfecho_falha_com_mensagem(df):
    sem_regressao = df.assign(reg_failed=0)
    with pytest.raises(ValueError, match="sem variação"):
        models.glmm_regressao(sem_regressao)


def test_diagnostico_tem_uma_linha_por_verificacao(df):
    from analysis import diagnostico
    glmm, gee = models.glmm_regressao(df), models.glmm_sensibilidade(df)
    d = diagnostico.diagnosticar(df, glmm, gee, "GLMM")
    assert {"modelo", "verificacao", "valor", "ok", "se_falhar"} <= set(d.columns)
    assert d["modelo"].str.startswith("crescimento").sum() == 15
    assert d.loc[d["verificacao"] == "otimizador convergiu", "ok"].all()
