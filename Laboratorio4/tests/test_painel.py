import json
import re

from src.painel import GRADE_N, GRADE_RAZOES, GRADE_SIGMA, gerar, montar_dados


def test_dados_do_painel_tem_tudo_que_as_secoes_usam():
    d = montar_dados()
    assert d["reais"]["n"] == {"com_bot": 30, "sem_bot": 30}
    assert len(d["q2"]) == 10 and len(d["q3"]) == 30 and len(d["q1"]) == 2
    assert abs(d["g2"]["p"] - 0.184) < 0.001
    json.dumps(d)  # serializável


def test_gerar_escreve_html_com_dados_embutidos(tmp_path):
    caminho = gerar(tmp_path / "dashboard.html")
    html = caminho.read_text(encoding="utf-8")
    assert "__DADOS__" not in html
    assert re.search(r"const D = \{", html)
    for secao in ("cenario", "tipo1", "poder", "conclusao", "bonus"):
        assert f'data-tab="{secao}"' in html


def test_alfa_menor_so_diminui_as_taxas():
    d = montar_dados()
    menor = {(l["situacao"], l["razao_medianas"], l["teste"]): l["taxa"] for l in d["alfa_menor"]["linhas"]}
    cinco = {}
    for r in d["q3"]:
        cinco[(r["situacao"], r["razao_medianas"], r["teste"])] = r["taxa"]
    for r in d["q2"]:
        cinco[("base", r["razao_medianas"], r["teste"])] = r["poder"]
    for chave, taxa in menor.items():
        assert taxa <= cinco[chave], chave
