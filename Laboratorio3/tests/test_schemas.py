"""Contrato dos CSVs: colunas, tipos e invariantes semânticas."""
import pandas as pd
import pytest

from metricas.schemas import (
    SCHEMAS,
    ErroDeContrato,
    df_vazio,
    validar,
    validar_csv,
)

ESPERADOS = [
    "candidatos", "repos", "funil", "descartes", "issues_bug",
    "releases", "releases_ignoradas", "tags", "commits", "deployments",
    "runs", "run_attempts", "episodios", "custo_api",
    "metricas", "metricas_mensais",
]


def test_todos_os_csvs_tem_schema():
    assert sorted(SCHEMAS) == sorted(ESPERADOS)


@pytest.mark.parametrize("nome", ESPERADOS)
def test_toda_coluna_esta_documentada(nome):
    schema = SCHEMAS[nome]
    assert schema.colunas, f"{nome} não tem colunas"
    for col, meta in schema.colunas.items():
        assert meta.tipo, f"{nome}.{col} sem tipo"
        assert meta.unidade, f"{nome}.{col} sem unidade"
        assert meta.origem, f"{nome}.{col} sem origem"


@pytest.mark.parametrize("nome", ESPERADOS)
def test_todo_csv_tem_chave_repo_menos_funil_e_custo(nome):
    sem_repo = {"funil", "custo_api"}
    tem = "repo" in SCHEMAS[nome].colunas
    assert tem is (nome not in sem_repo)


def test_metricas_tem_as_26_colunas():
    assert len(SCHEMAS["metricas"].colunas) == 26
    for col in ["rework_rate", "rework_rate_7d", "nota_freq", "nota_lead_time",
                "nota_cfr", "nota_recuperacao", "classe_dora", "classe_dora_nota"]:
        assert col in SCHEMAS["metricas"].colunas


def test_metricas_mensais_tem_o_contrato_combinado():
    assert list(SCHEMAS["metricas_mensais"].colunas) == [
        "repo", "mes", "cfr_a", "recuperacao_h", "runs_validos"
    ]


# --- validação estrutural ---

def test_df_valido_passa(df_metricas):
    validar(df_metricas, SCHEMAS["metricas"])


def test_df_vazio_com_colunas_certas_passa():
    # Repositório sem releases é caso legítimo do funil.
    validar(df_vazio(SCHEMAS["releases"]), SCHEMAS["releases"])


def test_coluna_faltando_nomeia_a_coluna(df_metricas):
    with pytest.raises(ErroDeContrato) as e:
        validar(df_metricas.drop(columns=["cfr_b"]), SCHEMAS["metricas"])
    assert "cfr_b" in str(e.value)


def test_coluna_extra_e_erro_no_modo_estrito(df_metricas):
    df = df_metricas.assign(coluna_nova=1)
    with pytest.raises(ErroDeContrato) as e:
        validar(df, SCHEMAS["metricas"])
    msg = str(e.value)
    assert "coluna_nova" in msg
    assert "dicionario_dados" in msg, "o erro deve dizer o que fazer"


def test_coluna_extra_passa_fora_do_modo_estrito(df_metricas):
    validar(df_metricas.assign(coluna_nova=1), SCHEMAS["metricas"], estrito=False)


def test_tipo_errado_diz_esperado_e_encontrado(df_metricas):
    df = df_metricas.assign(freq_release="muito")
    with pytest.raises(ErroDeContrato) as e:
        validar(df, SCHEMAS["metricas"])
    msg = str(e.value)
    assert "freq_release" in msg and "float" in msg


def test_ordem_das_colunas_nao_importa(df_metricas):
    validar(df_metricas[list(reversed(df_metricas.columns))], SCHEMAS["metricas"])


def test_nan_em_coluna_numerica_passa(df_metricas):
    # Repositório pode legitimamente não ter uma métrica.
    validar(df_metricas.assign(cfr_b=float("nan")), SCHEMAS["metricas"])


def test_inteiro_anulavel_lido_como_float_passa(df_metricas):
    # pandas lê int com nulo como float64; não pode virar erro falso.
    df = df_metricas.assign(nota_cfr=float("nan"))
    validar(df, SCHEMAS["metricas"])


# --- regras semânticas ---

def test_classe_dora_incoerente_com_a_nota_da_erro(df_metricas):
    df = df_metricas.assign(classe_dora="Elite")  # nota continua 3
    with pytest.raises(ErroDeContrato) as e:
        validar(df, SCHEMAS["metricas"])
    assert "classe_dora" in str(e.value)


def test_nota_fora_do_intervalo_da_erro(df_metricas):
    with pytest.raises(ErroDeContrato) as e:
        validar(df_metricas.assign(nota_freq=7), SCHEMAS["metricas"])
    assert "nota_freq" in str(e.value)


def test_mes_com_poucos_runs_exige_metrica_nula():
    df = pd.DataFrame([{
        "repo": "owner/nome", "mes": "2025-01",
        "cfr_a": 0.3, "recuperacao_h": 2.0, "runs_validos": 3,
    }])
    with pytest.raises(ErroDeContrato) as e:
        validar(df, SCHEMAS["metricas_mensais"])
    assert "runs_validos" in str(e.value)


def test_mes_com_poucos_runs_e_metrica_nula_passa():
    df = pd.DataFrame([{
        "repo": "owner/nome", "mes": "2025-01",
        "cfr_a": float("nan"), "recuperacao_h": float("nan"), "runs_validos": 3,
    }])
    validar(df, SCHEMAS["metricas_mensais"])


# --- leitura de disco ---

def test_validar_csv_le_do_disco(tmp_path, df_metricas):
    caminho = tmp_path / "metricas.csv"
    df_metricas.to_csv(caminho, index=False)
    validar_csv(caminho, SCHEMAS["metricas"])


def test_validar_csv_acusa_coluna_faltando(tmp_path, df_metricas):
    caminho = tmp_path / "metricas.csv"
    df_metricas.drop(columns=["cfr_b"]).to_csv(caminho, index=False)
    with pytest.raises(ErroDeContrato) as e:
        validar_csv(caminho, SCHEMAS["metricas"])
    assert "cfr_b" in str(e.value)


# --- correções da revisão final ---

def test_valor_texto_em_coluna_numerica_vira_erro_de_contrato(tmp_path):
    """Uma célula de texto numa coluna numérica é violação de contrato,
    não um TypeError vindo de dentro do pandas."""
    caminho = tmp_path / "metricas_mensais.csv"
    caminho.write_text(
        "repo,mes,cfr_a,recuperacao_h,runs_validos\n"
        "o/n,2025-01,0.3,2.0,3\n"
        "o/n,2025-02,,,desconhecido\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeContrato) as e:
        validar_csv(caminho, SCHEMAS["metricas_mensais"])
    assert "runs_validos" in str(e.value)


def test_texto_em_classe_dora_nota_vira_erro_de_contrato(df_metricas):
    """int('High') daria ValueError; o contrato precisa acusar o tipo."""
    df = df_metricas.assign(classe_dora_nota="High")
    with pytest.raises(ErroDeContrato) as e:
        validar(df, SCHEMAS["metricas"])
    assert "classe_dora_nota" in str(e.value)


def test_float_nao_inteiro_em_coluna_int_da_erro(df_metricas):
    """nota_freq=2.5 quebraria o kappa ponderado da RQ07, que depende da ordem
    de inteiros 1-4."""
    with pytest.raises(ErroDeContrato) as e:
        validar(df_metricas.assign(nota_freq=2.5), SCHEMAS["metricas"])
    assert "nota_freq" in str(e.value)


def test_float_inteiro_em_coluna_int_passa(df_metricas):
    """pandas lê int com nulo como float64: 3.0 continua sendo 3."""
    validar(df_metricas.assign(nota_freq=3.0), SCHEMAS["metricas"])
