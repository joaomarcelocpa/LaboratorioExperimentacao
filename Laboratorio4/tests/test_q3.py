from src.q3 import calcular_q3


def test_q3_tem_colunas_e_cobre_h0_e_efeitos():
    df = calcular_q3(situacoes={"pequena": {"n": 10, "sigma": 2.5}}, razoes=[1.0, 3.0])
    assert list(df.columns) == ["situacao", "razao_medianas", "teste", "taxa"]
    assert set(df["razao_medianas"]) == {1.0, 3.0}
    assert set(df["teste"]) == {"welch", "mann_whitney"}
    assert df["taxa"].between(0, 1).all()
