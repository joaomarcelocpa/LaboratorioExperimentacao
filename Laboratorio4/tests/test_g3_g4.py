from src.g3_g4 import carregar, plotar_g3, plotar_g4


def test_g3_e_g4_geram_arquivos(tmp_path):
    erro, todas = carregar()
    assert set(erro["situacao"]) == set(todas["situacao"])
    for caminho in (plotar_g3(erro, tmp_path), plotar_g4(todas, tmp_path)):
        assert caminho.exists() and caminho.stat().st_size > 0
