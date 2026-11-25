import pandas as pd

from analysis import pilot
from analysis.synthetic import Parametros, gerar


def _piloto(**kw):
    # piloto: 3 cadeias × 2 modos × 4 pedidos
    return gerar(3, passos=4, parametros=Parametros(**kw), seed=11)


def test_cinco_criterios_com_resultado_valido():
    cs = pilot.avaliar(_piloto(), orcamento_usd_cadeia=100, limite_horas_cadeia=10)
    assert len(cs) == 5
    assert {c.resultado for c in cs} <= {"PASSA", "FALHA", "PENDENTE"}


def test_custo_fica_pendente_sem_orcamento():
    c = pilot.custo_e_tempo(_piloto())
    assert c.resultado == "PENDENTE"


def test_execucao_falha_com_muitas_falhas():
    df = gerar(3, passos=4, parametros=Parametros(p_falha_execucao=0.5), seed=2)
    assert pilot.execucao_do_agente(df).resultado == "FALHA"


def test_piso_quando_nada_acontece():
    df = _piloto()
    df.loc[df["step"] >= 1, ["reg_failed", "arch_violations"]] = 0
    assert pilot.sem_piso_nem_teto(df).resultado == "FALHA"


def test_teto_quando_todas_as_cadeias_regridem_no_passo_1():
    df = _piloto()
    df.loc[df["step"] == 1, "reg_failed"] = 5
    c = pilot.sem_piso_nem_teto(df)
    assert c.resultado == "FALHA" and "teto" in c.valor


def test_determinismo_falha_com_flaky():
    df = _piloto()
    df.loc[df.index[df["step"] == 2][0], "flaky"] = 1
    assert pilot.determinismo(df).resultado == "FALHA"


def test_decisao_sugerida():
    ok = lambda n: pilot.Criterio(n, "PASSA", "", "")
    ruim = lambda n: pilot.Criterio(n, "FALHA", "", "")
    pend = pilot.Criterio("x", "PENDENTE", "", "")
    assert pilot.sugerir_decisao([ok("a")] * 5) == "GO"
    assert pilot.sugerir_decisao([ok("a"), ruim("Determinismo dos testes")]) == "GO com ajustes"
    assert pilot.sugerir_decisao([ruim("Execução do agente"), ruim("Custo e tempo")]) == "NO-GO"
    assert pilot.sugerir_decisao([pend]).startswith("INDEFINIDA")


def test_pipeline_completo_gera_saidas(tmp_path):
    from analysis.run import analisar
    out = analisar(gerar(6, seed=9), tmp_path)
    assert {"glmm", "log_rank", "testes_holm", "diferenca_pareada"} <= set(out)
    assert (tmp_path / "figures" / "kaplan_meier.png").exists() and (tmp_path / "testes_holm.csv").exists()
