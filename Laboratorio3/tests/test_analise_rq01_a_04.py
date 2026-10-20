"""RQ 01 a 04 e classificação C1, com dados de resultado conhecido."""
import pandas as pd

from analise import rq01_rq02, rq03_rq04


def _df():
    return pd.DataFrame({
        "repo": ["a/a", "b/b", "c/c"],
        "freq_release": [8.0, 0.5, 0.1],
        "lt_release_h": [10.0, 200.0, 800.0],
        "lt_commit_h": [12.0, 100.0, 700.0],
        "cfr_a": [0.10, 0.20, 0.50],
        "cfr_b": [0.0, 0.5, 1.0],
        "recuperacao_h": [0.5, 5.0, float("nan")],
        "pct_censurados": [0.0, 0.0, float("nan")],
        "nota_freq": [4, 2, 1],
    })


def test_tabela_rq02_converte_para_dias():
    t = rq01_rq02.tabela_rq02(_df())
    assert t.loc["lt_release_h", "mediana"] == 200.0
    assert t.loc["lt_release_h", "mediana_dias"] == 200.0 / 24


def test_comparar_variantes_conta_a_maior_que_b():
    c = rq01_rq02.comparar_variantes(_df())
    assert c["n"] == 3
    assert c["a_maior_que_b"] == 2


def test_faixas_de_frequencia_somam_todos_os_repos():
    f = rq01_rq02.faixas_frequencia(_df())
    assert f["repositorios"].sum() == 3
    assert f.loc[f["faixa"].str.startswith("Elite"), "repositorios"].item() == 1


def test_reclassificacao_c1_aplica_a_tabela_do_enunciado():
    r = rq03_rq04.reclassificar_c1(_df()).set_index("repo")
    # a/a: freq 4, lead 4 (10 h < 1 dia), cfr 4 (10% ≤ 15%), recup 4 (0,5 h < 1 h)
    assert r.loc["a/a", "classe_dora"] == "Elite"
    # c/c: freq 1, lead 1 (≥ 30 dias), cfr 1 (> 45%), recuperação ausente fica de fora
    assert r.loc["c/c", "classe_dora"] == "Low"


def test_recuperacao_ausente_nao_vira_nota():
    r = rq03_rq04.reclassificar_c1(_df()).set_index("repo")
    assert pd.isna(r.loc["c/c", "nota_recuperacao"])


def test_contagem_de_classes_tem_as_quatro_linhas():
    df = pd.DataFrame({"classe_dora": ["High", "High", "Low"]})
    c = rq03_rq04.contagem_classes(df)
    assert list(c.index) == ["Elite", "High", "Medium", "Low"]
    assert c.loc["High", "repositorios"] == 2
    assert c.loc["Elite", "repositorios"] == 0


def test_divergencias_zero_quando_o_csv_confere():
    df = pd.read_csv(rq03_rq04.comum.DADOS / "metricas.csv")
    assert rq03_rq04.divergencias(df, rq03_rq04.reclassificar_c1(df)) == 0
