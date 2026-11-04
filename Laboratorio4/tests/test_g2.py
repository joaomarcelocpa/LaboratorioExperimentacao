from src.g2 import plotar_g2


def test_g2_gera_arquivo(tmp_path):
    caminho = plotar_g2(t_obs=-1.361, gl=29.0, destino=tmp_path)
    assert caminho.exists() and caminho.stat().st_size > 0
