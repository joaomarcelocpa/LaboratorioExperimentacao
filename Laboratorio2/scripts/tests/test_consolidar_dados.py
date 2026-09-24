from consolidar_dados import _nome_arquivo, _parse_testes, carregar_trials


def test_parse_testes_com_barra():
    assert _parse_testes("83/83") == (83, 83)


def test_parse_testes_sem_barra_assume_trial_nao_censurado():
    assert _parse_testes("123") == (123, 123)


def test_nome_arquivo_joao_bernardo_usa_tratamento_e_dificuldade():
    assert _nome_arquivo("joao", 2011, "facil", usou_ia=False) == "manual-easy.py"
    assert _nome_arquivo("bernardo", 306, "media", usou_ia=True) == "ai-medium.py"


def test_nome_arquivo_miguel_usa_mapa_por_kata():
    assert _nome_arquivo("miguel", 2011, "facil", usou_ia=True) == "finalValueOfVariable.py"


def test_carregar_trials_retorna_12_trials():
    linhas = carregar_trials()
    assert len(linhas) == 12


def test_cada_kata_tem_exatamente_um_trial_manual_e_um_com_ia():
    linhas = carregar_trials()
    por_kata = {}
    for linha in linhas:
        por_kata.setdefault(linha["kata_id"], set()).add(linha["tratamento"])

    assert len(por_kata) == 6
    for tratamentos in por_kata.values():
        assert tratamentos == {"manual", "ia"}


def test_linhas_tem_metricas_estaticas_associadas():
    linhas = carregar_trials()
    for linha in linhas:
        assert linha["loc"] > 0
        assert linha["cc_media"] >= 0
        assert 0 <= linha["taxa_sucesso"] <= 100
