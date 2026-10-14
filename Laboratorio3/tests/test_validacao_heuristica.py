import io
import math
import pandas as pd
import pytest
from metricas.validacao_heuristica import (
    _extrair_commits,
    calcular_metricas_variante,
    validar,
)


# --- _extrair_commits ---

def test_extrair_commits_lista_com_hifens():
    texto = "- fix: crash\n- feat: algo\n- revert: undo"
    msgs = _extrair_commits(texto)
    assert msgs == ["fix: crash", "feat: algo", "revert: undo"]


def test_extrair_commits_texto_vazio():
    assert _extrair_commits("") == []
    assert _extrair_commits("nan") == []


def test_extrair_commits_sem_prefixo():
    texto = "fix: crash\nfeat: algo"
    msgs = _extrair_commits(texto)
    assert msgs == ["fix: crash", "feat: algo"]


# --- calcular_metricas_variante ---

def test_metricas_perfeitas():
    v = [True, True, False, False]
    p = [True, True, False, False]
    m = calcular_metricas_variante(v, p)
    assert m["precision"] == pytest.approx(1.0)
    assert m["recall"] == pytest.approx(1.0)
    assert m["f1"] == pytest.approx(1.0)


def test_metricas_todos_errados():
    v = [True, True, False, False]
    p = [False, False, True, True]
    m = calcular_metricas_variante(v, p)
    assert m["precision"] == pytest.approx(0.0)
    assert m["recall"] == pytest.approx(0.0)
    assert m["f1"] == pytest.approx(0.0)


def test_metricas_50pct_precision_100pct_recall():
    # TP=2, FP=2, FN=0 → P=0.5, R=1.0, F1=0.667
    v = [True,  True,  False, False]
    p = [True,  True,  True,  True]
    m = calcular_metricas_variante(v, p)
    assert m["precision"] == pytest.approx(0.5)
    assert m["recall"] == pytest.approx(1.0)
    assert abs(m["f1"] - 2 / 3) < 0.01


# --- validar ---

_CSV_MINIMO = """\
repo,tag,publicada_em,corretiva,commits,notas
owner/repo-a,v1.0.0,2024-01-01T00:00:00Z,False,"- feat: initial release",""
owner/repo-a,v1.0.1,2024-01-10T00:00:00Z,True,"- fix: crash","bug fix release"
owner/repo-a,v1.1.0,2024-02-01T00:00:00Z,False,"- feat: new feature",""
owner/repo-b,v2.0.0,2024-03-01T00:00:00Z,False,"- feat: init",""
owner/repo-b,v2.0.1,2024-03-05T00:00:00Z,True,"- hotfix: memory leak","hotfix"
"""


def _df_minimo() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(_CSV_MINIMO))


def test_validar_retorna_dataframe_com_variantes(tmp_path):
    csv = tmp_path / "labels.csv"
    csv.write_text(_CSV_MINIMO)
    tabela = validar(csv, verbose=False)
    assert list(tabela["variante"]) == ["v1", "v2", "v3", "v4", "v5"]


def test_validar_colunas_esperadas(tmp_path):
    csv = tmp_path / "labels.csv"
    csv.write_text(_CSV_MINIMO)
    tabela = validar(csv, verbose=False)
    for col in ("F1 (todos)", "P (todos)", "R (todos)",
                "F1 (decidíveis)", "P (decidíveis)", "R (decidíveis)"):
        assert col in tabela.columns, f"coluna '{col}' ausente"


def test_validar_f1_entre_0_e_1(tmp_path):
    csv = tmp_path / "labels.csv"
    csv.write_text(_CSV_MINIMO)
    tabela = validar(csv, verbose=False)
    for _, row in tabela.iterrows():
        assert 0.0 <= row["F1 (todos)"] <= 1.0
        assert 0.0 <= row["F1 (decidíveis)"] <= 1.0


def test_validar_ignora_linhas_sem_rotulo(tmp_path):
    csv_com_nan = _CSV_MINIMO + "owner/repo-a,v1.2.0,2024-04-01T00:00:00Z,,- feat: x,\n"
    csv = tmp_path / "labels.csv"
    csv.write_text(csv_com_nan)
    # deve rodar sem erro (lança aviso no stderr, mas não exceção)
    tabela = validar(csv, verbose=False)
    assert len(tabela) == 5  # ainda retorna 5 variantes
