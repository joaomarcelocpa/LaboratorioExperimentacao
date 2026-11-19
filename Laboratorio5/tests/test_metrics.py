import shutil
import subprocess

import pytest

from metrics import arquitetura, complexidade, deriva, duplicacao, grafo, localidade
from metrics.coletar import COLUNAS, coletar
from metrics.java import camada, carregar_projeto, modulo, pacote_base_comum
from tests.fixtures import BASE, criar_workspace, novo_commit

SPRING_NO_DOMINIO = {
    "domain/Tarefa.java": "package com.exemplo.tarefas.domain;\nimport org.springframework.stereotype.Component;\npublic class Tarefa {}\n",
}
CONTROLLER_COM_REPO = {
    "adapter/web/TarefaController.java": "package com.exemplo.tarefas.adapter.web;\nimport com.exemplo.tarefas.adapter.persistence.TarefaRepository;\npublic class TarefaController { TarefaRepository r; }\n",
    "adapter/persistence/TarefaRepository.java": "package com.exemplo.tarefas.adapter.persistence;\npublic class TarefaRepository {}\n",
}
CICLO = {
    "domain/A.java": "package com.exemplo.tarefas.domain;\nimport com.exemplo.tarefas.application.B;\npublic class A { B b; }\n",
    "application/B.java": "package com.exemplo.tarefas.application;\nimport com.exemplo.tarefas.domain.A;\npublic class B { A a; }\n",
}


def test_pacote_base_e_camadas(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w"))
    assert p.pacote_base == BASE
    assert pacote_base_comum({"a.b.c", "a.b.d"}) == "a.b"
    assert camada(BASE + ".domain", BASE) == "domain"
    assert camada(BASE + ".adapter.web", BASE) == "entrada"
    assert camada(BASE + ".adapter.persistence", BASE) == "saida"
    assert modulo(BASE + ".adapter.web", BASE) == "adapter.web"
    assert modulo(BASE + ".domain", BASE) == "domain"


def test_semente_limpa_tem_zero_violacoes_e_zero_ciclos(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w"))
    r = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    assert r.violacoes == 0 and r.fonte == "estatica"
    assert grafo.ciclos(grafo.grafo_dos_fontes(p)) == 0


def test_r1_framework_no_dominio(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w", extras=SPRING_NO_DOMINIO))
    r = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    assert r.por_regra["R1"] == 1 and r.violacoes == 1


def test_r3_e_r5_controller_acessa_repositorio(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w", extras=CONTROLLER_COM_REPO))
    r = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    assert r.por_regra["R3"] == 1 and r.por_regra["R5"] == 1


def test_r2_application_importando_biblioteca(tmp_path):
    extra = {"application/CriarTarefa.java": "package com.exemplo.tarefas.application;\nimport org.springframework.stereotype.Service;\npublic class CriarTarefa {}\n"}
    p = carregar_projeto(criar_workspace(tmp_path / "w", extras=extra))
    assert arquitetura.verificar_estaticamente(p, usar_jdeps=False).por_regra["R2"] == 1


def test_ciclo_entre_pacotes(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w", extras=CICLO))
    g = grafo.grafo_dos_fontes(p)
    assert grafo.ciclos(g) == 1
    assert grafo.componentes_ciclicos(g) == [[BASE + ".application", BASE + ".domain"]]
    r = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    assert r.por_regra["R4"] == 1 and r.por_regra["R1"] == 1 and r.por_regra["R2"] == 0


def test_tarjan_com_tres_pacotes():
    g = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}
    assert grafo.componentes_ciclicos(g) == [["a", "b", "c"]]
    assert grafo.ciclos({"a": {"b"}, "b": set()}) == 0


def test_contagem_de_violacoes_do_archunit():
    texto = (
        "Rule 'classes that reside in domain should not depend on adapter' was violated (3 times):\n...\n"
        "Rule 'no cycles' was violated (1 times):\n"
        "Architecture Violation [Priority: MEDIUM] - Rule 'x' was violated (2 times):"
    )
    assert arquitetura.contar_violacoes_archunit(texto) == 6
    assert arquitetura.contar_violacoes_archunit("tudo certo") == 0


def test_complexidade_e_loc(tmp_path):
    p = criar_workspace(tmp_path / "w")
    r = complexidade.medir(p)
    assert r["max_ccn"] == 2  # um if em Tarefa.peso
    assert r["loc"] > 10


def test_localidade_do_commit(tmp_path):
    raiz = criar_workspace(tmp_path / "w")
    novo_commit(raiz, {
        "domain/Tarefa.java": "package com.exemplo.tarefas.domain;\npublic class Tarefa { int v; }\n",
        "adapter/web/TarefaController.java": "package com.exemplo.tarefas.adapter.web;\npublic class TarefaController {}\n",
        "README.md": "mudou",
    })
    r = localidade.medir(raiz, BASE)
    assert r == {"files_touched": 2, "modules_touched": 2}  # .md fica de fora


def test_localidade_primeiro_commit_conta_tudo(tmp_path):
    raiz = criar_workspace(tmp_path / "w")
    assert localidade.medir(raiz, BASE)["files_touched"] == 5


def test_deriva_modulo_nao_documentado_e_regra_violada(tmp_path):
    arq_doc = "# Arq\nMódulos: domain e application.\n"
    raiz = criar_workspace(tmp_path / "w", extras=SPRING_NO_DOMINIO, architecture=arq_doc)
    p = carregar_projeto(raiz)
    arq = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    d = deriva.medir(p, arq)
    assert d["modulos_nao_documentados"] == ["adapter.persistence", "adapter.web"]
    assert d["doc_drift"] == 1 + 2  # R1 violada + 2 módulos fora do documento


def test_deriva_documento_completo_e_zero(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w"))
    arq = arquitetura.verificar_estaticamente(p, usar_jdeps=False)
    assert deriva.medir(p, arq)["doc_drift"] == 0


def test_deriva_sem_documento(tmp_path):
    p = carregar_projeto(criar_workspace(tmp_path / "w", architecture=None))
    d = deriva.medir(p, arquitetura.verificar_estaticamente(p, usar_jdeps=False))
    assert d["documento"] is False and d["doc_drift"] == 4


@pytest.mark.skipif(shutil.which("javac") is None or shutil.which("jdeps") is None, reason="JDK ausente")
def test_jdeps_sobre_classes_compiladas(tmp_path):
    raiz = criar_workspace(tmp_path / "w", extras=CICLO)
    fontes = [str(f) for f in (raiz / "src/main/java").rglob("*.java")]
    saida = raiz / "target" / "classes"
    saida.mkdir(parents=True)
    subprocess.run(["javac", "-d", str(saida), *fontes], check=True, capture_output=True)
    p = carregar_projeto(raiz)
    g, fonte = grafo.dependencias(p)
    assert fonte == "jdeps"
    assert grafo.ciclos(g) == 1
    assert BASE + ".domain" in g[BASE + ".application"]


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx ausente")
def test_jscpd_detecta_duplicacao(tmp_path):
    corpo = "".join(f"    int a{i} = x * {i} + y - {i}; if (a{i} > 3) {{ y += a{i}; }}\n" for i in range(12))
    classe = lambda n: f"package com.exemplo.tarefas.domain;\npublic class {n} {{\n  int f(int x, int y) {{\n{corpo}    return y;\n  }}\n}}\n"
    dup = criar_workspace(tmp_path / "dup", extras={"domain/X.java": classe("X"), "domain/Y.java": classe("Y")})
    limpo = criar_workspace(tmp_path / "limpo")
    assert duplicacao.medir(dup) > 20
    assert duplicacao.medir(limpo) == 0


def test_coletar_devolve_as_8_colunas_do_esquema(tmp_path):
    from analysis.schema import NOMES
    raiz = criar_workspace(tmp_path / "w", extras=SPRING_NO_DOMINIO)
    r = coletar(raiz, com_jscpd=False, com_archunit=False, com_jdeps=False)
    assert set(COLUNAS) <= set(NOMES)  # compatível com o esquema de dados
    assert r["arch_violations"] == 1 and r["cycles"] == 0 and r["loc"] > 0
    assert r["detalhe"]["fonte_arch_violations"] == "estatica"
    assert r["dup_pct"] is None  # jscpd desligado
