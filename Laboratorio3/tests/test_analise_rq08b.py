"""RQ 08b: tendência temporal das métricas de CI por repositório (#77)."""
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from analise import comum, rq08b

MESES = [f"2025-{m:02d}" for m in (10, 11, 12)] + [f"2026-{m:02d}" for m in range(1, 10)]


def _serie(valores):
    """Série mensal (índice = mês) a partir de até 12 valores."""
    return pd.Series(list(valores), index=MESES[: len(valores)], dtype=float)


def _mensal(repo, valores, coluna="cfr_a"):
    return pd.DataFrame({"repo": repo, "mes": MESES[: len(valores)],
                         coluna: list(valores),
                         "runs_validos": 20})


# --- um repositório ---------------------------------------------------------------

def test_queda_do_cfr_e_melhora_com_a_inclinacao_de_sen_em_pontos_percentuais():
    # o exemplo do plano: 30%, 28%, 25%, ... 14% em 12 meses
    pct = [30, 28, 25, 27, 22, 20, 21, 18, 17, 15, 16, 14]
    r = rq08b.teste_tendencia(_serie([p / 100 for p in pct]), "cfr_a")
    assert r["testado"] and r["n_meses"] == 12
    assert r["direcao"] == "melhora"
    assert r["p"] < 0.05
    assert r["inclinacao"] == pytest.approx(-1.4143, abs=1e-3)      # p.p. por mês


def test_alta_do_cfr_e_piora():
    r = rq08b.teste_tendencia(_serie(np.linspace(0.05, 0.40, 12)), "cfr_a")
    assert r["direcao"] == "piora" and r["inclinacao"] > 0


def test_recuperacao_cai_em_horas_por_mes():
    r = rq08b.teste_tendencia(_serie(np.linspace(48, 4, 12)), "recuperacao_h")
    assert r["direcao"] == "melhora"
    assert r["inclinacao"] == pytest.approx(-4.0, abs=1e-6)         # h/mês, sem escala


def test_ruido_sem_tendencia():
    r = rq08b.teste_tendencia(_serie([20, 25, 18, 24, 19, 26, 21, 23, 20, 25, 19, 24]), "recuperacao_h")
    assert r["direcao"] == "sem tendência" and r["p"] >= 0.05


def test_serie_constante_nao_tem_tendencia_e_nao_levanta():
    r = rq08b.teste_tendencia(_serie([0.1] * 12), "cfr_a")
    assert r["testado"] and r["direcao"] == "sem tendência" and r["p"] == 1.0


def test_menos_de_oito_meses_validos_fica_fora_do_teste():
    nan = float("nan")
    sete = [0.3, 0.2, nan, 0.25, 0.2, nan, 0.15, 0.1, nan, nan, 0.05, nan]
    assert pd.Series(sete).notna().sum() == 7
    r = rq08b.teste_tendencia(_serie(sete), "cfr_a")
    assert r["testado"] is False and r["n_meses"] == 7 and r["direcao"] == "não testado"
    assert math.isnan(r["p"])


def test_exatamente_oito_meses_validos_entra():
    nan = float("nan")
    oito = [0.30, 0.28, nan, 0.22, 0.20, nan, 0.15, 0.12, 0.10, nan, 0.08, nan]
    assert pd.Series(oito).notna().sum() == 8
    assert rq08b.teste_tendencia(_serie(oito), "cfr_a")["testado"] is True


def test_mes_sem_valor_nao_conta_como_zero():
    # o mês de dados insuficientes é NaN; tratá-lo como 0 inventaria uma melhora
    nan = float("nan")
    r = rq08b.teste_tendencia(_serie([0.2, 0.2, nan, nan, nan, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]), "cfr_a")
    assert r["direcao"] == "sem tendência" and r["n_meses"] == 9


def test_hamed_rao_acompanha_o_teste_original():
    r = rq08b.teste_tendencia(_serie(np.linspace(0.05, 0.40, 12)), "cfr_a")
    assert 0.0 <= r["p_hamed_rao"] <= 1.0
    assert isinstance(r["autocorrelacao"], bool)


def test_autocorrelacao_forte_dos_residuos_e_sinalizada():
    alternada = [0.25 if t % 2 else 0.15 for t in range(12)]       # r1 dos resíduos ≈ -0,9
    assert rq08b.teste_tendencia(_serie(alternada), "cfr_a")["autocorrelacao"] is True


def test_ruido_branco_nao_e_sinalizado_como_autocorrelacao():
    ruido = [0.1804, 0.1948, 0.2499, 0.2198, 0.1508, 0.1998, 0.1813, 0.2045,
             0.1518, 0.2073, 0.2071, 0.2473]                       # r1 ≈ 0
    assert rq08b.teste_tendencia(_serie(ruido), "cfr_a")["autocorrelacao"] is False


def test_hamed_rao_sem_resultado_vira_nan_e_nao_emite_aviso(recwarn):
    # com variância corrigida negativa o pymannkendall devolve NaN e avisa; aqui só o NaN fica
    r = rq08b.teste_tendencia(_serie([20, 25, 18, 24, 19, 26, 21, 23, 20, 25, 19, 24]), "recuperacao_h")
    assert math.isnan(r["p_hamed_rao"])
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)]


# --- vários repositórios e correção de Holm -------------------------------------------

def test_holm_bate_com_o_calculo_a_mao():
    p = pd.Series([0.01, 0.04, 0.03, 0.5])
    # ordenados: .01*4=.04 ; .03*3=.09 ; .04*2=.08 -> max até aqui .09 ; .5*1=.5
    assert rq08b.aplicar_holm(p).round(4).tolist() == [0.04, 0.09, 0.09, 0.5]


def test_tendencias_por_repo_ordena_os_meses_e_marca_quem_ficou_fora():
    boa = _mensal("a/boa", np.linspace(0.40, 0.05, 12))
    curta = _mensal("b/curta", [0.1, 0.2, 0.3])
    embaralhado = pd.concat([boa, curta]).sample(frac=1, random_state=1)
    t = rq08b.tendencias_por_repo(embaralhado, "cfr_a").set_index("repo")
    assert t.loc["a/boa", "direcao"] == "melhora"            # a ordem das linhas não importa
    assert t.loc["b/curta", "testado"] == False              # noqa: E712
    assert math.isnan(t.loc["b/curta", "p_holm"])
    assert list(t.columns[:3]) == ["n_meses", "testado", "p"]


def test_holm_pode_derrubar_o_que_o_p_bruto_deixava_passar():
    # 40 repositórios com tendência fraca e p bruto um pouco abaixo de 0,05
    rng = np.random.default_rng(3)
    linhas = []
    for i in range(40):
        base = np.linspace(0.30, 0.22, 12) + rng.normal(0, 0.05, 12)
        linhas.append(_mensal(f"r/{i:02d}", np.clip(base, 0, 1)))
    t = rq08b.tendencias_por_repo(pd.concat(linhas), "cfr_a")
    assert (t["p"] < 0.05).sum() > (t["p_holm"] < 0.05).sum()


def test_resumo_traz_proporcoes_com_e_sem_holm_e_o_funil():
    t = pd.DataFrame({
        "repo": list("abcdefgh"),
        "testado": [True] * 6 + [False] * 2,
        "direcao": ["melhora", "melhora", "piora", "sem tendência", "sem tendência", "sem tendência",
                    "não testado", "não testado"],
        "direcao_holm": ["melhora", "sem tendência", "sem tendência", "sem tendência",
                         "sem tendência", "sem tendência", "não testado", "não testado"],
    })
    r = rq08b.resumo(t, "cfr_a").iloc[0]
    assert (r["repos"], r["testados"], r["excluidos"]) == (8, 6, 2)
    assert r["melhora"] == 2 and r["piora"] == 1 and r["sem_tendencia"] == 3
    assert r["pct_melhora"] == pytest.approx(2 / 6)
    assert r["melhora_holm"] == 1 and r["piora_holm"] == 0 and r["sem_tendencia_holm"] == 5


# --- visão da amostra -------------------------------------------------------------------

def test_serie_da_amostra_e_mediana_e_iqr_por_mes():
    mensais = pd.concat([_mensal("a", [0.1, 0.2]), _mensal("b", [0.3, 0.4]),
                         _mensal("c", [0.5, float("nan")])])
    s = rq08b.serie_amostra(mensais, "cfr_a").set_index("mes")
    assert s.loc["2025-10", "n"] == 3 and s.loc["2025-10", "mediana"] == pytest.approx(0.3)
    assert s.loc["2025-10", "q1"] == pytest.approx(0.2) and s.loc["2025-10", "q3"] == pytest.approx(0.4)
    assert s.loc["2025-11", "n"] == 2           # NaN fica de fora e o n diz quantos sobraram


def test_tendencia_da_serie_da_amostra():
    s = pd.DataFrame({"mes": MESES, "mediana": np.linspace(0.30, 0.10, 12)})
    r = rq08b.tendencia_amostra(s, "cfr_a")
    assert r["direcao"] == "melhora" and r["p"] < 0.05


# --- frequência e lead time por trimestre (descritivo, sem teste) ---------------------------

def _rel(repo, tag, quando, pre=False, na_janela=True):
    return {"repo": repo, "tag": tag, "publicada_em": quando, "prerelease": pre,
            "na_janela": na_janela, "body": ""}


def test_frequencia_por_trimestre_ignora_pre_release_e_fora_da_janela():
    ini, fim = date(2025, 10, 1), date(2026, 9, 30)
    rel = pd.DataFrame(
        [_rel("a/x", f"v{i}", f"2025-10-{i + 1:02d}T10:00:00Z") for i in range(13)]   # 13 no 4º tri/2025
        + [_rel("a/x", "pre", "2025-11-01T10:00:00Z", pre=True)]
        + [_rel("a/x", "antes", "2025-01-01T10:00:00Z", na_janela=False)])
    q = rq08b.frequencia_trimestral(rel, ini, fim).set_index("trimestre")
    assert q.index.tolist() == ["2025Q4", "2026Q1", "2026Q2", "2026Q3"]
    semanas = (92 * 86400 - 1) / (7 * 86400)    # 1/out 00:00 até 31/dez 23:59:59
    assert q.loc["2025Q4", "mediana"] == pytest.approx(13 / semanas, rel=1e-3)
    assert q.loc["2026Q1", "mediana"] == 0.0 and q.loc["2025Q4", "n_repos"] == 1


def test_lead_time_por_trimestre_usa_o_trimestre_da_publicacao():
    rel = pd.DataFrame([_rel("a/x", "v1", "2025-09-01T00:00:00Z", na_janela=False),
                        _rel("a/x", "v2", "2025-11-10T00:00:00Z"),
                        _rel("a/x", "v3", "2026-02-10T00:00:00Z")])
    com = pd.DataFrame([
        {"repo": "a/x", "release_tag": "v2", "sha": "1", "data_autor": "2025-11-08T00:00:00Z",
         "autor_login": "d", "eh_bot": False, "mensagem": "m"},
        {"repo": "a/x", "release_tag": "v3", "sha": "2", "data_autor": "2026-02-05T00:00:00Z",
         "autor_login": "d", "eh_bot": False, "mensagem": "m"}])
    t = rq08b.lead_time_trimestral(rel, com).set_index("trimestre")
    assert t.loc["2025Q4", "mediana_h"] == pytest.approx(48.0)
    assert t.loc["2026Q1", "mediana_h"] == pytest.approx(120.0)


# --- execução ---------------------------------------------------------------------------------

def test_main_grava_tabelas_e_figura_e_e_reexecutavel(tmp_path, monkeypatch):
    mensais = pd.concat([
        _mensal("a/queda", np.linspace(0.40, 0.05, 12)),
        _mensal("b/alta", np.linspace(0.05, 0.40, 12)),
        _mensal("c/curta", [0.1, 0.2]),
        _mensal("a/queda", np.linspace(48, 4, 12), "recuperacao_h"),
    ])
    mensais = (mensais.groupby(["repo", "mes"], as_index=False).first())
    rel = pd.DataFrame([_rel("a/queda", f"v{i}", f"2025-10-{i + 1:02d}T10:00:00Z") for i in range(6)])
    com = pd.DataFrame([{"repo": "a/queda", "release_tag": "v1", "sha": "1",
                         "data_autor": "2025-10-01T00:00:00Z", "autor_login": "d",
                         "eh_bot": False, "mensagem": "m"}])
    monkeypatch.setattr(comum, "SAIDA", tmp_path)
    monkeypatch.setattr(comum, "carregar_metricas_mensais", lambda: mensais)
    monkeypatch.setattr(rq08b, "carregar_releases", lambda: rel)
    monkeypatch.setattr(rq08b, "carregar_commits", lambda: com)
    monkeypatch.setattr(rq08b, "janela", lambda: (date(2025, 10, 1), date(2026, 9, 30)))

    rq08b.main()
    nomes = ["rq08b_tendencias", "rq08b_resumo", "rq08b_serie_amostra", "rq08b_amostra_mk",
             "rq08b_frequencia_trimestral", "rq08b_lead_time_trimestral"]
    for n in nomes:
        assert (tmp_path / "tabelas" / f"{n}.csv").exists(), n
    assert (tmp_path / "figuras" / "rq08b_serie_amostra.png").exists()
    antes = {n: (tmp_path / "tabelas" / f"{n}.csv").read_bytes() for n in nomes}
    rq08b.main()
    assert antes == {n: (tmp_path / "tabelas" / f"{n}.csv").read_bytes() for n in nomes}
    t = pd.read_csv(tmp_path / "tabelas" / "rq08b_tendencias.csv")
    assert set(t["metrica"]) == {"cfr_a", "recuperacao_h"}
