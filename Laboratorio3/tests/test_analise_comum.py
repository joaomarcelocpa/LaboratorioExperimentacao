"""Funções comuns da análise: resumo, tabelas e figuras."""
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from analise import __main__ as runner
from analise import comum


def test_resumo_calcula_mediana_iqr_e_n():
    r = comum.resumo(pd.Series([1, 2, 3, 4, 5]))
    assert r["n"] == 5
    assert r["mediana"] == 3
    assert (r["q1"], r["q3"], r["iqr"]) == (2, 4, 2)


def test_resumo_ignora_ausentes_e_informa_n():
    r = comum.resumo(pd.Series([1.0, None, 3.0]))
    assert r["n"] == 2
    assert r["mediana"] == 2.0


def test_resumo_de_serie_vazia_nao_quebra():
    r = comum.resumo(pd.Series([], dtype=float))
    assert r["n"] == 0
    assert pd.isna(r["mediana"])


def test_tabela_resumo_tem_uma_linha_por_coluna():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
    t = comum.tabela_resumo(df, ["a", "b"])
    assert list(t.index) == ["a", "b"]
    assert t.loc["b", "mediana"] == 20


def test_salvar_tabela_e_figura(tmp_path, monkeypatch):
    monkeypatch.setattr(comum, "SAIDA", tmp_path / "saida")
    t = comum.salvar_tabela(pd.DataFrame({"x": [1]}), "tab")
    fig, ax = plt.subplots()
    ax.plot([1, 2])
    f = comum.salvar_figura(fig, "fig")
    assert t.exists() and t.suffix == ".csv" and t.parent.name == "tabelas"
    assert f.exists() and f.suffix == ".png" and f.parent.name == "figuras"


def test_carregar_arquivo_ausente_explica_o_que_fazer(tmp_path, monkeypatch):
    monkeypatch.setattr(comum, "DADOS", tmp_path)
    with pytest.raises(FileNotFoundError, match="make run"):
        comum.carregar_metricas()


def test_carrega_o_metricas_csv_real():
    df = comum.carregar_metricas()
    assert "repo" in df.columns and len(df) > 0


def test_runner_sem_analises_termina_bem(monkeypatch, capsys):
    monkeypatch.setattr(runner, "descobrir", lambda: [])
    assert runner.main() == 0
    assert "Nenhuma análise" in capsys.readouterr().out


def test_runner_descobre_so_modulos_rq():
    assert all(n.startswith("rq") for n in runner.descobrir())
