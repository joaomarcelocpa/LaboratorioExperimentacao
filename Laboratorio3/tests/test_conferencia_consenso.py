"""Consenso e kappa da conferência manual, com respostas inventadas."""
import math

import pandas as pd
import pytest

from conferencia import consenso, kappa, rotulos
from conferencia.rotulos import ErroDeRotulo

REPOS = ["a/x", "b/y", "c/z", "d/w"]
TAGS = ["v1", "v2"]


def _escrever(pasta, nome, tipo, entregas, corretiva):
    """tipo/entregas: listas por repo; corretiva: lista por release (repo x tag)."""
    pd.DataFrame({"repo": REPOS, "tipo_projeto": tipo, "entregas_reais": entregas}) \
        .to_csv(pasta / f"rotulos_{nome}_repositorios.csv", index=False)
    chaves = [(r, t) for r in REPOS for t in TAGS]
    pd.DataFrame({"repo": [c[0] for c in chaves], "tag": [c[1] for c in chaves],
                  "corretiva": corretiva}) \
        .to_csv(pasta / f"rotulos_{nome}_releases.csv", index=False)


@pytest.fixture
def pasta(tmp_path):
    pd.DataFrame({"repo": REPOS, "tipo_projeto": "", "entregas_reais": ""}) \
        .to_csv(tmp_path / "planilha_repositorios.csv", index=False)
    chaves = [(r, t) for r in REPOS for t in TAGS]
    pd.DataFrame({"repo": [c[0] for c in chaves], "tag": [c[1] for c in chaves],
                  "corretiva": ""}).to_csv(tmp_path / "planilha_releases.csv", index=False)
    return tmp_path


def _tres(pasta, joao, bernardo, miguel):
    for nome, (t, e, c) in zip(["joao", "bernardo", "miguel"], [joao, bernardo, miguel]):
        _escrever(pasta, nome, t, e, c)


def _base():
    return (["biblioteca", "aplicacao", "cli", "outro"],
            ["sim", "sim", "nao", "incerto"],
            ["sim", "nao"] * 4)


def test_maioria_unanime_maioria_e_empate():
    assert consenso.maioria(["sim", "sim", "sim"]) == ("sim", "unanime")
    assert consenso.maioria(["sim", "nao", "sim"]) == ("sim", "maioria")
    assert consenso.maioria(["sim", "nao", "incerto"]) == (None, "empate")


def test_normalizar_aceita_acento_e_maiuscula():
    assert rotulos.normalizar(" Não ") == "nao"
    assert rotulos.normalizar("APLICAÇÃO") == "aplicacao"


def test_consenso_aplica_maioria_e_lista_so_o_que_diverge(pasta):
    t, e, c = _base()
    t2 = ["biblioteca", "cli", "cli", "outro"]       # Bernardo diverge no repo b/y
    t3 = ["biblioteca", "aplicacao", "aplicacao", "outro"]
    _tres(pasta, (t, e, c), (t2, e, c), (t3, e, c))
    consensos, div = consenso.calcular(rotulos.carregar(pasta))
    assert list(consensos["repositorios"]["tipo_projeto"]) == [
        "biblioteca", "aplicacao", "cli", "outro"]
    assert set(div["situacao"]) == {"maioria"}
    assert set(div["repo"]) == {"b/y", "c/z"}


def test_empate_fica_sem_consenso_ate_o_grupo_decidir(pasta):
    t, e, c = _base()
    t2 = ["biblioteca", "aplicacao", "outro", "outro"]
    t3 = ["biblioteca", "aplicacao", "aplicacao", "outro"]
    _tres(pasta, (t, e, c), (t2, e, c), (t3, e, c))   # c/z: cli, outro, aplicacao
    consensos, div = consenso.calcular(rotulos.carregar(pasta))
    assert pd.isna(consensos["repositorios"].loc["c/z", "tipo_projeto"])
    assert list(div.loc[div["situacao"] == "empate", "repo"]) == ["c/z"]

    decisao = {("tipo_projeto", "c/z", ""): "cli"}
    consensos, div = consenso.calcular(rotulos.carregar(pasta), decisao)
    assert consensos["repositorios"].loc["c/z", "tipo_projeto"] == "cli"
    assert list(div["situacao"]) == ["desempate"]


def test_gerar_escreve_arquivos_e_conta_empates(pasta):
    t, e, c = _base()
    t2 = ["biblioteca", "aplicacao", "outro", "outro"]
    t3 = ["biblioteca", "aplicacao", "aplicacao", "outro"]
    _tres(pasta, (t, e, c), (t2, e, c), (t3, e, c))
    resumo = consenso.gerar(pasta)
    assert resumo == {"itens_divergentes": 1, "empates_abertos": 1}
    for nome in ["consenso_repositorios", "consenso_releases", "divergencias",
                 "empates_para_reuniao"]:
        assert (pasta / f"{nome}.csv").exists()


def test_desempates_csv_e_lido_na_proxima_execucao(pasta):
    t, e, c = _base()
    t2 = ["biblioteca", "aplicacao", "outro", "outro"]
    t3 = ["biblioteca", "aplicacao", "aplicacao", "outro"]
    _tres(pasta, (t, e, c), (t2, e, c), (t3, e, c))
    pd.DataFrame([{"dimensao": "tipo_projeto", "repo": "c/z", "tag": "", "valor": "cli"}]) \
        .to_csv(pasta / "desempates.csv", index=False)
    assert consenso.gerar(pasta)["empates_abertos"] == 0
    final = pd.read_csv(pasta / "consenso_repositorios.csv").set_index("repo")
    assert final.loc["c/z", "tipo_projeto"] == "cli"


def test_resposta_invalida_e_linha_faltando_sao_recusadas(pasta):
    t, e, c = _base()
    _tres(pasta, (t, e, c), (t, e, c), (t, e, c))
    df = pd.read_csv(pasta / "rotulos_miguel_releases.csv")
    df.loc[0, "corretiva"] = "talvez"
    df.to_csv(pasta / "rotulos_miguel_releases.csv", index=False)
    with pytest.raises(ErroDeRotulo, match="talvez"):
        rotulos.carregar(pasta)

    _tres(pasta, (t, e, c), (t, e, c), (t, e, c))
    pd.read_csv(pasta / "rotulos_bernardo_releases.csv").iloc[:-1] \
        .to_csv(pasta / "rotulos_bernardo_releases.csv", index=False)
    with pytest.raises(ErroDeRotulo, match="bernardo/releases"):
        rotulos.carregar(pasta)


def test_celula_em_branco_e_recusada(pasta):
    t, e, c = _base()
    t_branco = ["", "aplicacao", "cli", "outro"]
    _tres(pasta, (t, e, c), (t_branco, e, c), (t, e, c))
    with pytest.raises(ErroDeRotulo, match="tipo_projeto"):
        rotulos.carregar(pasta)


def test_precisa_de_pelo_menos_dois_avaliadores(pasta):
    t, e, c = _base()
    _escrever(pasta, "joao", t, e, c)
    with pytest.raises(ErroDeRotulo, match="ao menos 2"):
        rotulos.carregar(pasta)


def test_kappa_concordancia_total_e_um(pasta):
    t, e, c = _base()
    _tres(pasta, (t, e, c), (t, e, c), (t, e, c))
    res = kappa.calcular(rotulos.carregar(pasta)).set_index("dimensao")
    assert res.loc["tipo_projeto", "kappa"] == pytest.approx(1.0)
    assert res.loc["corretiva", "kappa"] == pytest.approx(1.0)
    assert res.loc["corretiva", "pct_unanime"] == 1.0


def test_kappa_confere_com_conta_manual():
    # 2 avaliadores, 4 itens, 2 categorias: concordam em 3 de 4.
    # Fleiss soma as respostas dos dois: sim = 5/8, nao = 3/8, logo
    # Pe = (5/8)^2 + (3/8)^2 = 34/64; Po = 0,75; kappa = (Po - Pe) / (1 - Pe) = 7/15
    resp = pd.DataFrame({"a": ["sim", "sim", "nao", "nao"],
                         "b": ["sim", "sim", "nao", "sim"]})
    assert kappa.kappa_da_dimensao(resp, "corretiva")["kappa"] == pytest.approx(7 / 15)


def test_kappa_indefinido_quando_todos_respondem_a_mesma_coisa():
    resp = pd.DataFrame({"a": ["sim"] * 3, "b": ["sim"] * 3, "c": ["sim"] * 3})
    r = kappa.kappa_da_dimensao(resp, "corretiva")
    assert math.isnan(r["kappa"]) and "indefinido" in r["interpretacao"]


def test_interpretacao_segue_landis_e_koch():
    assert kappa.interpretar(0.1) == "leve"
    assert kappa.interpretar(0.5) == "moderada"
    assert kappa.interpretar(0.9) == "quase perfeita"
    assert kappa.interpretar(-0.2) == "pior que o acaso"


def test_main_do_kappa_escreve_csv(pasta, capsys):
    t, e, c = _base()
    _tres(pasta, (t, e, c), (t, e, c), (t, e, c))
    assert kappa.main(["--pasta", str(pasta)]) == 0
    assert (pasta / "kappa.csv").exists()
    assert "tipo_projeto: kappa 1.000" in capsys.readouterr().out
