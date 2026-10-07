"""O dicionário de dados é gerado — nunca editado à mão."""
from metricas.dicionario import CAMINHO_PADRAO, gerar_markdown
from metricas.schemas import SCHEMAS


def test_arquivo_em_disco_esta_sincronizado():
    atual = CAMINHO_PADRAO.read_text(encoding="utf-8")
    esperado = gerar_markdown()
    assert atual == esperado, (
        "docs/dicionario_dados.md está dessincronizado. "
        "Rode: python -m metricas.dicionario"
    )


def test_toda_coluna_de_todo_schema_aparece():
    texto = gerar_markdown()
    for schema in SCHEMAS.values():
        for coluna in schema.colunas:
            assert f"`{coluna}`" in texto, f"{schema.nome}.{coluna} não documentada"


def test_todo_csv_aparece_com_seu_dono():
    texto = gerar_markdown()
    for schema in SCHEMAS.values():
        assert schema.nome in texto
        assert f"**Dono:** {schema.dono}" in texto


def test_pipe_no_texto_e_escapado():
    # Um | solto corromperia a tabela Markdown.
    from metricas.dicionario import _tabela
    from metricas.schemas import Coluna, Schema

    schema = Schema("teste.csv", "C", {
        "col": Coluna("str", "a|b", "origem com | pipe"),
    })
    linha = _tabela(schema)
    assert r"\|" in linha
