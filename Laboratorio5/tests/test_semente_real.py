"""As métricas contra a semente real do Lab05 (seed/), sem alterá-la.

Violações são injetadas numa cópia temporária, como a semente faz nos próprios
testes do ArchUnit, para provar que a checagem estática enxerga cada regra.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from metrics.coletar import coletar
from metrics.java import carregar_projeto

SEMENTE = Path(__file__).resolve().parent.parent / "seed"
BASE = "labexp.semente"
pytestmark = pytest.mark.skipif(not SEMENTE.is_dir(), reason="seed/ ausente")


def _copia(tmp_path: Path, injetar: dict[str, str] | None = None, remover_doc: bool = False) -> Path:
    destino = tmp_path / "w"
    shutil.copytree(SEMENTE, destino, ignore=shutil.ignore_patterns("target"))
    for rel, texto in (injetar or {}).items():
        arq = destino / "src/main/java/labexp/semente" / rel
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(texto)
    if remover_doc:
        (destino / "ARCHITECTURE.md").unlink()
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
        subprocess.run([*git, *args], cwd=destino, check=True, capture_output=True)
    return destino


def _medir(raiz):
    return coletar(raiz, com_jscpd=False, com_archunit=False, com_jdeps=False)


def test_semente_tem_zero_violacoes_ciclos_e_deriva(tmp_path):
    r = _medir(_copia(tmp_path))
    assert r["detalhe"]["pacote_base"] == BASE
    assert (r["arch_violations"], r["cycles"], r["doc_drift"]) == (0, 0, 0)
    assert r["detalhe"]["violacoes"] == []


def test_semente_localidade_funciona_em_workspace_proprio(tmp_path):
    r = _medir(_copia(tmp_path))
    assert r["files_touched"] > 20
    assert r["modules_touched"] == 5  # domain, application, adapter.in, adapter.out, config


def _regras(r):
    return {k: v for k, v in r["detalhe"]["violacoes_por_regra"].items() if v}


def test_r1_spring_no_dominio(tmp_path):
    r = _medir(_copia(tmp_path, {"domain/Contaminada.java": "package labexp.semente.domain;\nimport org.springframework.stereotype.Component;\npublic class Contaminada {}\n"}))
    assert _regras(r) == {"R1": 1} and r["arch_violations"] == 1


def test_r2_application_importando_biblioteca(tmp_path):
    r = _medir(_copia(tmp_path, {"application/service/Ruim.java": "package labexp.semente.application.service;\nimport org.springframework.stereotype.Service;\npublic class Ruim {}\n"}))
    assert _regras(r) == {"R2": 1}


def test_r5_controlador_chamando_o_servico(tmp_path):
    r = _medir(_copia(tmp_path, {"adapter/in/web/Atalho.java": "package labexp.semente.adapter.in.web;\nimport labexp.semente.application.service.TarefaService;\npublic class Atalho { TarefaService s; }\n"}))
    assert _regras(r) == {"R5": 1}


def test_r3_persistencia_chamando_porta_de_entrada(tmp_path):
    r = _medir(_copia(tmp_path, {"adapter/out/persistence/Atalho.java": "package labexp.semente.adapter.out.persistence;\nimport labexp.semente.application.port.in.CriarTarefa;\npublic class Atalho { CriarTarefa c; }\n"}))
    assert _regras(r) == {"R3": 1}


def test_r4_ciclo_entre_adaptadores(tmp_path):
    # entrada -> saida (R3 e R5) e saida -> entrada (R3) fecham um ciclo entre adapter.in e adapter.out
    r = _medir(_copia(tmp_path, {
        "adapter/in/web/Ida.java": "package labexp.semente.adapter.in.web;\nimport labexp.semente.adapter.out.persistence.Volta;\npublic class Ida { Volta v; }\n",
        "adapter/out/persistence/Volta.java": "package labexp.semente.adapter.out.persistence;\nimport labexp.semente.adapter.in.web.Ida;\npublic class Volta { Ida i; }\n",
    }))
    assert r["detalhe"]["violacoes_por_regra"]["R4"] == 1
    assert r["cycles"] == 1


def test_deriva_modulo_novo_sem_documentacao(tmp_path):
    r = _medir(_copia(tmp_path, {"relatorio/Gerador.java": "package labexp.semente.relatorio;\npublic class Gerador {}\n"}))
    assert r["detalhe"]["modulos_nao_documentados"] == ["relatorio"]
    assert r["doc_drift"] == 1


def test_deriva_sem_architecture_md(tmp_path):
    r = _medir(_copia(tmp_path, remover_doc=True))
    assert r["detalhe"]["documento_arquitetura"] is False
    assert r["doc_drift"] == 5


def test_metricas_nao_alteram_a_semente_do_repositorio():
    antes = subprocess.run(["git", "status", "--porcelain", "--", str(SEMENTE)], capture_output=True, text=True).stdout
    carregar_projeto(SEMENTE)
    depois = subprocess.run(["git", "status", "--porcelain", "--", str(SEMENTE)], capture_output=True, text=True).stdout
    assert antes == depois
