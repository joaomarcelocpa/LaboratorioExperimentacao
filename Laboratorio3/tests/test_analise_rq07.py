"""RQ 07: sensibilidade da classificação DORA às definições operacionais (#76)."""
import math

import numpy as np
import pandas as pd
import pytest

from analise import comum, rq07
from analise.rq03_rq04 import reclassificar_c1


def _repo(nome, freq=8, freq_pre=None, freq_tag=None, lt_a=10, lt_b=None,
          cfr_a=0.05, cfr_b=None, rec=3.0):
    """Um repositório com as colunas de metricas.csv que as combinações usam."""
    return {
        "repo": nome,
        "freq_release": freq,
        "freq_release_pre": freq if freq_pre is None else freq_pre,
        "freq_tag": freq if freq_tag is None else freq_tag,
        "lt_release_h": lt_a,
        "lt_commit_h": lt_a if lt_b is None else lt_b,
        "cfr_a": cfr_a,
        "cfr_b": cfr_a if cfr_b is None else cfr_b,
        "recuperacao_h": rec,
    }


def _df(*linhas):
    return pd.DataFrame(list(linhas))


def oraculo_kappa_linear(a, b, k=4):
    """Kappa ponderado linear escrito à mão, com categorias 1..k fixas."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        obs[x - 1, y - 1] += 1
    esp = np.outer(obs.sum(1), obs.sum(0)) / n
    peso = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    return 1 - (peso * obs).sum() / (peso * esp).sum()


# --- as três combinações ---------------------------------------------------------

def test_combinacoes_usam_as_colunas_do_enunciado():
    assert rq07.COMBINACOES["C1"] == {
        "freq": "freq_release", "lead_time": "lt_release_h", "cfr": "cfr_a"}
    assert rq07.COMBINACOES["C2"] == {
        "freq": "freq_release_pre", "lead_time": "lt_commit_h", "cfr": "cfr_b"}
    assert rq07.COMBINACOES["C3"] == {
        "freq": "freq_tag", "lead_time": "lt_commit_h", "cfr": "cfr_a"}
    assert rq07.RECUPERACAO == "recuperacao_h"


def test_c1_igual_a_classificacao_de_referencia_da_rq03_rq04():
    df = _df(
        _repo("elite"),
        _repo("high", freq=2, lt_a=48, cfr_a=0.10, rec=10),
        _repo("medium", freq=0.5, lt_a=300, cfr_a=0.40, rec=50),
        _repo("low", freq=0.1, lt_a=900, cfr_a=0.80, rec=400),
        _repo("sem_rec", rec=float("nan")),
    )
    c1 = rq07.classificar_combinacao(df, rq07.COMBINACOES["C1"])
    ref = reclassificar_c1(df)
    assert c1["classe_dora"].tolist() == ref["classe_dora"].tolist()
    assert c1["classe_dora_nota"].tolist() == ref["classe_dora_nota"].tolist()


def test_cfr_b_alto_rebaixa_na_c2_mas_nao_na_c1():
    df = _df(_repo("a/x", cfr_a=0.05, cfr_b=0.50))     # notas C1 (4,4,4,3); C2 (4,4,1,3)
    classes = rq07.classificar_todas(df).iloc[0]
    assert classes["classe_C1"] == "Elite"
    assert classes["classe_C2"] == "High"              # mediana de (1,3,4,4) = 3,5 -> 3
    assert classes["nota_C2"] == 3


def test_poucas_tags_rebaixam_na_c3_mas_nao_na_c1():
    # C1: (freq 4, lt 3, cfr 4, rec 4) -> Elite. C3 troca a frequência por 0,1 tag/semana
    # (nota 1): (1, 3, 4, 4) -> mediana 3,5 -> High
    df = _df(_repo("a/x", freq=8, freq_tag=0.1, lt_a=48, cfr_a=0.10, rec=0.5))
    c = rq07.classificar_todas(df).iloc[0]
    assert (c["classe_C1"], c["classe_C3"]) == ("Elite", "High")
    assert c["classe_C2"] == "Elite"                   # a C2 usa freq_release_pre (=8)


def test_recuperacao_ausente_sai_da_mediana_em_todas_as_combinacoes():
    df = _df(_repo("a/x", rec=float("nan")))
    c = rq07.classificar_todas(df).iloc[0]
    assert c["classe_C1"] == "Elite"
    assert c["classe_C2"] == "Elite" and c["classe_C3"] == "Elite"


def test_repositorio_sem_nenhuma_nota_fica_sem_classe():
    nan = float("nan")
    df = _df(_repo("a/x", freq=nan, freq_pre=nan, freq_tag=nan, lt_a=nan, lt_b=nan,
                   cfr_a=nan, cfr_b=nan, rec=nan))
    c = rq07.classificar_todas(df).iloc[0]
    assert c["classe_C1"] is None and math.isnan(c["nota_C1"])


# --- comparação entre pares ---------------------------------------------------------

def test_pares_identicos_nao_mudam_e_tem_kappa_um():
    notas = pd.Series([1, 2, 3, 4, 3, 2])
    r = rq07.comparar_par(notas, notas.copy())
    assert r["n"] == 6 and r["mudaram"] == 0 and r["pct_mudou"] == 0.0
    assert r["kappa"] == pytest.approx(1.0)
    assert r["subiram"] == 0 and r["desceram"] == 0


def test_percentual_e_sentido_da_mudanca():
    a = pd.Series([4, 4, 3, 2, 1])
    b = pd.Series([3, 4, 4, 2, 1])
    r = rq07.comparar_par(a, b)
    assert r["mudaram"] == 2 and r["pct_mudou"] == pytest.approx(0.4)
    assert r["desceram"] == 1 and r["subiram"] == 1     # 4->3 desce; 3->4 sobe


def test_kappa_ponderado_bate_com_o_oraculo():
    a = [4, 4, 3, 3, 2, 2, 1, 1, 3, 4]
    b = [4, 3, 3, 2, 2, 1, 1, 1, 4, 4]
    r = rq07.comparar_par(pd.Series(a), pd.Series(b))
    assert r["kappa"] == pytest.approx(oraculo_kappa_linear(a, b))


def test_kappa_usa_categorias_fixas_mesmo_quando_falta_uma_no_meio():
    # só aparecem Low, Medium e Elite (falta a nota 3): sem labels=[1..4] o sklearn
    # trata 1, 2 e 4 como igualmente espaçadas e dá 0,4074 em vez de 0,2381
    a = [1, 2, 4, 4, 2, 4, 2, 1]
    b = [1, 4, 2, 2, 4, 4, 2, 1]
    r = rq07.comparar_par(pd.Series(a), pd.Series(b))
    assert r["kappa"] == pytest.approx(0.2381, abs=1e-4)
    assert r["kappa"] == pytest.approx(oraculo_kappa_linear(a, b))


def test_repositorio_sem_classe_em_um_lado_fica_fora_do_par():
    a = pd.Series([4, 3, np.nan, 2])
    b = pd.Series([4, 2, 3, np.nan])
    r = rq07.comparar_par(a, b)
    assert r["n"] == 2 and r["mudaram"] == 1


def test_sem_variacao_nenhuma_o_kappa_e_nan_e_nao_levanta_aviso(recwarn):
    r = rq07.comparar_par(pd.Series([3, 3, 3]), pd.Series([3, 3, 3]))
    assert math.isnan(r["kappa"]) and r["pct_mudou"] == 0.0
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)]


def test_par_sem_nenhum_repositorio_em_comum():
    r = rq07.comparar_par(pd.Series([np.nan]), pd.Series([3.0]))
    assert r["n"] == 0 and math.isnan(r["pct_mudou"]) and math.isnan(r["kappa"])


def test_tabela_de_pares_tem_os_tres_pares_na_ordem_do_enunciado():
    df = _df(_repo("a"), _repo("b", cfr_a=0.5, cfr_b=0.5, lt_a=900))
    t = rq07.tabela_pares(rq07.classificar_todas(df))
    assert t.index.tolist() == ["C1xC2", "C1xC3", "C2xC3"]
    assert list(t.columns) == ["n", "mudaram", "pct_mudou", "subiram", "desceram",
                               "kappa", "concordancia"]


@pytest.mark.parametrize("kappa, texto", [
    (-0.1, "pobre"), (0.10, "leve"), (0.30, "razoável"), (0.50, "moderada"),
    (0.70, "substancial"), (0.90, "quase perfeita"), (float("nan"), "indefinida"),
])
def test_leitura_do_kappa_pela_escala_de_landis_e_koch(kappa, texto):
    assert rq07.leitura_kappa(kappa) == texto


def test_mudanca_por_metrica_diz_onde_a_definicao_pesa():
    # C1 -> C2 só muda o CFR (a -> b): a nota de freq e a de lead time ficam
    df = _df(_repo("a", cfr_a=0.05, cfr_b=0.50), _repo("b", cfr_a=0.05, cfr_b=0.05))
    t = rq07.mudanca_por_metrica(df).set_index(["par", "metrica"])
    assert t.loc[("C1xC2", "cfr"), "pct_nota_mudou"] == pytest.approx(0.5)
    assert t.loc[("C1xC2", "freq"), "pct_nota_mudou"] == 0.0
    assert t.loc[("C1xC2", "lead_time"), "pct_nota_mudou"] == 0.0
    assert t.loc[("C1xC3", "cfr"), "pct_nota_mudou"] == 0.0     # a mesma coluna cfr_a


def test_contagem_por_combinacao_soma_os_repositorios_classificados():
    df = _df(_repo("a"), _repo("b", freq=0.1, lt_a=900, cfr_a=0.8, rec=400))
    t = rq07.contagem_por_combinacao(rq07.classificar_todas(df))
    assert t.index.tolist() == ["Elite", "High", "Medium", "Low"]
    assert t.sum().tolist() == [2, 2, 2]


def test_matriz_de_transicao():
    df = _df(_repo("a", cfr_a=0.05, cfr_b=0.50), _repo("b"))
    m = rq07.matriz_transicao(rq07.classificar_todas(df), "C1", "C2")
    assert m.loc["Elite", "High"] == 1 and m.loc["Elite", "Elite"] == 1
    assert int(m.values.sum()) == 2


# --- execução ---------------------------------------------------------------------------

def test_main_grava_as_tabelas_e_e_reexecutavel(tmp_path, monkeypatch):
    df = _df(_repo("a", cfr_a=0.05, cfr_b=0.50), _repo("b"),
             _repo("c", freq=0.5, lt_a=300, cfr_a=0.4, rec=50))
    monkeypatch.setattr(comum, "SAIDA", tmp_path)
    monkeypatch.setattr(comum, "carregar_metricas", lambda: df)
    rq07.main()
    esperados = ["rq07_classes", "rq07_pares", "rq07_classes_por_combinacao",
                 "rq07_mudanca_por_metrica", "rq07_transicoes"]
    for nome in esperados:
        assert (tmp_path / "tabelas" / f"{nome}.csv").exists(), nome
    assert (tmp_path / "figuras" / "rq07_classes_por_combinacao.png").exists()
    antes = {n: (tmp_path / "tabelas" / f"{n}.csv").read_bytes() for n in esperados}
    rq07.main()
    assert antes == {n: (tmp_path / "tabelas" / f"{n}.csv").read_bytes() for n in esperados}
    pares = pd.read_csv(tmp_path / "tabelas" / "rq07_pares.csv", index_col=0)
    assert pares.index.tolist() == ["C1xC2", "C1xC3", "C2xC3"]
