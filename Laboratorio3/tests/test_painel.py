"""Painel estático (Issue #79): dados derivados, marcas da página e pasta versionada."""
import html
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analise.painel import conteudo, dados, gerar

RAIZ = Path(__file__).resolve().parent.parent
JS = (RAIZ / "analise/painel/estatico/page.js").read_text(encoding="utf-8")
SHIM = (RAIZ / "analise/painel/estatico/shim.js").read_text(encoding="utf-8")


# --- derivados, com fixtures de resposta conhecida -----------------------------------------------

def _m():
    nan = float("nan")
    return pd.DataFrame({
        "repo": list("abcde"),
        "freq_release": [8, 0.5, 0.2, 1.5, 0.1], "freq_tag": [9, 0.4, 0.3, 1.5, 0.05],
        "lt_release_h": [10, 100, 200, 300, 400], "lt_commit_h": [10, 90, 210, 100, 400],
        "cfr_a": [0.05, 0.12, 0.2, 0.3, 0.0], "cfr_a_bruto": [0.06, 0.12, 0.2, 0.3, 0.0],
        "cfr_a_sem_flaky": [0.05, 0.10, 0.2, 0.3, 0.0], "cfr_b": [0.1, 0.5, 0.9, 0.2, 0.0],
        "recuperacao_h": [0.5, 5, nan, 30, 200], "pct_censurados": [0, 0.1, 0, 0, 0],
        "rework_rate": [1, 1, 0.5, 0.2, 1],
    })


def _obs():
    ep = pd.DataFrame({"censurado": [True, False, False, False], "so_flaky": [False, False, True, False]})
    t6 = pd.DataFrame({"epsilon2": [0.01, 0.2, 0.05], "p_ajustado": [1.0, 0.001, 0.5]})
    c7 = pd.DataFrame({"nota_C1": [1, 2, 3, 4], "nota_C2": [1, 2, 3, 3], "nota_C3": [1, 2, 3, 4]})
    o = dados.observados(_m(), ep, t6, c7)
    return dict(zip(o["id"], o["valor"]))


@pytest.mark.parametrize("chave, esperado", [
    ("n_repos", 5), ("rq01_n_elite", 1), ("rq01_pct_tag_ge_release", 0.6),
    ("rq02_mediana_dias", 200 / 24), ("rq02_pct_1a7d", 0.2), ("rq02_pct_a_maior_b", 0.4), ("rq02_dif_pct", 0.5),
    ("rq03a_pct_10a25", 0.4), ("rq03a_pct_abaixo10", 0.4), ("rq03a_queda_flaky_pp", 2.0), ("rq03b_pct_abaixo30", 0.6),
    ("rq04_n_repos", 4), ("rq04_n_eps", 4), ("rq04_eps_censurados", 1), ("rq04_pct_eps_censurados", 0.25),
    ("rq04_eps_so_flaky", 1), ("rq04_repos_com_censura", 1), ("rq04_repos_acima_1dia", 2),
    ("rq04_repos_acima_1sem", 1), ("rq04_n_high", 1), ("rq04_pct_high", 0.25), ("rq04_sem_recuperacao", 1),
    ("rq06_n_testes", 3), ("rq06_eps_baixo", 2), ("rq06_sig_holm", 1),
    ("rq07_n_mudou_algum", 1), ("rq07_pct_mudou_algum", 0.25),
    ("rq08a_pct_rework_1", 0.6), ("rq08a_n_rework_1", 3), ("rq08a_pct_maior_cfr_b", 0.6), ("rq08a_dif_pp", 80.0),
])
def test_observados_batem_com_a_conta_feita_a_mao(chave, esperado):
    assert _obs()[chave] == pytest.approx(esperado, abs=1e-5)


def test_borda_de_elite_e_de_um_dia_segue_os_cortes_do_enunciado():
    m = _m().assign(freq_release=[7, 6.99, 0, 0, 0], recuperacao_h=[1, 24, 168, 0.99, 23.99])
    ep = pd.DataFrame({"censurado": [False], "so_flaky": [False]})
    o = dados.observados(m, ep, pd.DataFrame({"epsilon2": [0], "p_ajustado": [1]}),
                         pd.DataFrame({"nota_C1": [1], "nota_C2": [1], "nota_C3": [1]}))
    o = dict(zip(o["id"], o["valor"]))
    assert o["rq01_n_elite"] == 1            # 7 por semana entra, 6,99 não
    assert o["rq04_repos_acima_1dia"] == 1   # só 168 (> 24); o 24 exato não é "acima"
    assert o["rq04_repos_acima_1sem"] == 1   # 168 entra
    assert o["rq04_n_high"] == 2             # 1 h entra e 23,99 entra; 24 e 0,99 não


def test_rho_do_rework_fica_entre_menos_um_e_um():
    assert -1 <= _obs()["rq08a_rho_cfr_b"] <= 1


def test_medianas_de_uma_coluna_conhecida():
    m = pd.DataFrame({c: [1, 2, 3, 4, 5] for c in dados.METRICAS_MEDIANAS})
    r = dados.medianas(m).set_index("metrica").loc["cfr_a"]
    assert (r["n"], r["mediana"], r["q1"], r["q3"], r["media"], r["p90"]) == (5, 3, 2, 4, 3, 4.6)


def test_medianas_ignoram_ausentes_e_dizem_o_n():
    m = pd.DataFrame({c: [1.0, 2.0, 3.0, np.nan] for c in dados.METRICAS_MEDIANAS})
    r = dados.medianas(m).set_index("metrica").loc["cfr_b"]
    assert r["n"] == 3 and r["mediana"] == 2


def test_grupos_da_rq06_por_linguagem_e_por_quartil_de_idade():
    m = pd.DataFrame({"repo": [f"r{i}" for i in range(1, 9)], "freq_release": [1, 2, 3, 4, 5, 6, 7, 8],
                      "lt_commit_h": [10, 20, 30, 40, 50, 60, 70, 80],
                      "cfr_b": [.1, .2, .3, .4, .5, .6, .7, .8]})
    repos = pd.DataFrame({"repo": m["repo"], "linguagem": ["Go"] * 3 + ["Py"] * 3 + ["Rust"] * 2,
                          "idade_anos": [1, 2, 3, 4, 5, 6, 7, 8]})
    g = dados.grupos_rq06(m, repos).set_index(["fator", "grupo"])
    assert g.loc[("linguagem", "Go"), "freq_release"] == 2 and g.loc[("linguagem", "Go"), "n"] == 3
    assert g.loc[("linguagem", "Rust"), "freq_release"] == 7.5
    assert g.loc[("idade", "Q1"), "freq_release"] == 1.5 and g.loc[("idade", "Q4"), "freq_release"] == 7.5
    assert (g.loc[("idade", "Q1"), "idade_min"], g.loc[("idade", "Q1"), "idade_max"]) == (1, 2)


def test_a_v5_e_a_melhor_variante_da_heuristica():
    h = dados.heuristica_f1().set_index("variante")
    assert h["f1"].idxmax() == "v5" and (h["f1"] < 0.70).all()   # nenhuma chega ao limiar do enunciado


# --- a página gerada -----------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    destino = tmp_path_factory.mktemp("dashboard")
    gerar.construir(destino)
    return destino


MARCA = re.compile(r'<span class="v" data-source="([^"]+)"(?: data-where="([^"]*)")? data-field="([^"]+)" data-fmt="([^"]+)">')
FORMATOS = set(re.findall(r"^\s{4}(\w+): \(v\)", JS, flags=re.M))


def test_todo_conjunto_do_gerador_vira_um_csv(pagina):
    assert sorted(p.stem for p in (pagina / "data").glob("*.csv")) == sorted(dados.FONTES)


def test_toda_marca_aponta_para_uma_linha_e_uma_coluna_reais(pagina):
    texto = (pagina / "index.html").read_text(encoding="utf-8")
    marcas = MARCA.findall(texto)
    assert len(marcas) > 200
    cache: dict[str, pd.DataFrame] = {}
    for fonte, onde, campo, fmt in marcas:
        df = cache.setdefault(fonte, pd.read_csv(pagina / "data" / f"{fonte}.csv", dtype=str, keep_default_na=False))
        filtro = dict(p.split("=", 1) for p in html.unescape(onde).split("&")) if onde else {}
        linhas = df
        for k, v in filtro.items():
            assert k in df.columns, f"{fonte}: coluna de filtro {k!r} não existe"
            linhas = linhas[linhas[k] == v]
        assert len(linhas) >= 1, f"nenhuma linha em {fonte} para {filtro}"
        assert campo in df.columns, f"{fonte}: coluna {campo!r} não existe"
        valor = linhas.iloc[0][campo]
        if fmt != "txt":
            assert valor != "" and float(valor) == float(valor), f"{fonte} {filtro} {campo} não é número: {valor!r}"
        assert fmt in FORMATOS | {"txt"}, f"formato {fmt!r} não existe no JS"


def test_toda_aba_tem_modelo_e_ids_sao_unicos(pagina):
    texto = (pagina / "index.html").read_text(encoding="utf-8")
    ids = [t[0] for t in conteudo.TABS]
    assert len(ids) == len(set(ids))
    for i in ids:
        assert f'<template id="tpl-{i}">' in texto and f'data-tab="{i}"' in texto


def test_todo_grafico_pede_uma_predefinicao_que_o_js_conhece(pagina):
    texto = (pagina / "index.html").read_text(encoding="utf-8")
    tipos = set(re.findall(r"^  const CHARTS = \{(.+)\};", JS, flags=re.M)[0].replace(":", ",").split(","))
    tipos = {t.strip().split()[0] for t in tipos if t.strip() and t.strip()[0].isalpha()}
    def chaves(nome):
        bloco = re.search(rf"const {nome} = \{{\n(.*?)\n  \}};", JS, flags=re.S).group(1)
        return set(re.findall(r"^    (\w+)[(:]", bloco, flags=re.M))
    barras, hist = chaves("BARS"), chaves("HIST")
    for m in re.finditer(r'<div class="px-chart" data-chart="(\w+)" data-source="[^"]+"([^>]*)>', texto):
        kind, resto = m.group(1), m.group(2)
        assert kind in tipos, f"tipo de gráfico desconhecido: {kind}"
        preset = re.search(r'data-preset="(\w+)"', resto)
        if kind == "hist":
            assert preset.group(1) in hist
        if kind == "bars":
            assert preset.group(1) in barras


def test_sem_innerhtml_e_com_script_externo_travado(pagina):
    texto = (pagina / "index.html").read_text(encoding="utf-8")
    assert "innerHTML" not in JS + SHIM and "insertAdjacentHTML" not in JS + SHIM
    externos = re.findall(r'<script src="([^"]+)"([^>]*)>', texto)
    assert len(externos) == 1
    url, resto = externos[0]
    assert url.startswith("https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/") and 'integrity="sha384-' in resto
    assert not re.search(r"https?://(?!cdnjs\.cloudflare\.com|github\.com/joaomarcelocpa|www\.w3\.org)", texto)


def test_scripts_tem_sintaxe_valida():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node não instalado")
    for nome in ("page.js", "shim.js"):
        r = subprocess.run([node, "--check", str(RAIZ / "analise/painel/estatico" / nome)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_a_pasta_versionada_esta_em_sincronia_com_o_gerador(pagina):
    versionada = RAIZ / "dashboard"
    assert versionada.exists(), "rode: python -m analise.painel"
    for novo in sorted(pagina.rglob("*")):
        if novo.is_file():
            velho = versionada / novo.relative_to(pagina)
            assert velho.exists(), f"{velho} não existe; rode: python -m analise.painel"
            assert velho.read_bytes().replace(b"\r\n", b"\n") == novo.read_bytes(), (
                f"{velho.name} está desatualizado; rode: python -m analise.painel")
