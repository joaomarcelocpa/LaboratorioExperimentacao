from datetime import date
import pandas as pd
from metricas.frequencia import frequencia

INICIO = date(2024, 1, 1)
FIM = date(2024, 12, 28)  # 52 semanas exatas


def _df_releases(datas_iso: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"publicada_em": datas_iso})


def test_52_releases_em_52_semanas():
    datas = pd.date_range("2024-01-01", periods=52, freq="W").strftime("%Y-%m-%dT00:00:00Z").tolist()
    df = _df_releases(datas)
    resultado = frequencia(df, INICIO, FIM)
    assert abs(resultado - 1.0) < 0.05


def test_evento_exatamente_no_fim_da_janela():
    df = _df_releases(["2024-12-28T23:59:59Z"])
    resultado = frequencia(df, INICIO, FIM)
    assert resultado > 0, "evento no fim deve ser incluído"


def test_evento_apos_fim_excluido():
    df = _df_releases(["2025-01-01T00:00:00Z"])
    resultado = frequencia(df, INICIO, FIM)
    assert resultado == 0.0


def test_df_vazio_retorna_zero():
    df = pd.DataFrame({"publicada_em": []})
    resultado = frequencia(df, INICIO, FIM)
    assert resultado == 0.0


def test_periodo_trimestral_retorna_series():
    datas = [
        "2024-01-15T00:00:00Z", "2024-01-20T00:00:00Z",  # Q1: 2
        "2024-04-10T00:00:00Z",                            # Q2: 1
    ]
    df = _df_releases(datas)
    serie = frequencia(df, INICIO, FIM, periodo="Q")
    assert hasattr(serie, "iloc"), "deve retornar pd.Series"
    q1_total = serie[serie.index.astype(str).str.startswith("2024Q1")].sum()
    assert q1_total == 2


def test_coluna_data_customizavel():
    df = pd.DataFrame({"data_commit": ["2024-06-01T00:00:00Z"]})
    resultado = frequencia(df, INICIO, FIM, coluna_data="data_commit")
    assert resultado > 0
