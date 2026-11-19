"""Violações das regras de arquitetura (ARCHITECTURE.md, PLANEJAMENTO.pdf 3.3).

Medida oficial: as violações que o ArchUnit reporta ao rodar o teste de
arquitetura da semente (`mvn test`). Quando o Maven não está disponível,
`verificar_estaticamente` aplica as mesmas 5 regras sobre os imports dos
fontes; os dois caminhos devolvem a fonte usada.

Regras, espelhando seed/src/test/java/labexp/semente/ArquiteturaTest.java:
  R1 domain só depende de domain e do JDK (java..).
  R2 application só depende de application, domain e do JDK.
  R3 entrada não depende de saída; saída não depende de entrada, de
     application.port.in nem de application.service.
  R4 sem ciclos entre os pacotes de primeiro nível nem entre adapter.in e adapter.out.
  R5 adaptadores de entrada não dependem de application.port.out, application.service,
     adaptadores de saída, Spring Data nem JPA.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from metrics.grafo import ciclos, dependencias, grafo_de_modulos
from metrics.java import Projeto, camada, pacote_do_import, relativo

REGRAS = {
    "R1": "domain só depende de domain e do JDK",
    "R2": "application só depende de application, domain e do JDK",
    "R3": "entrada e saída independentes (saída também não usa port.in nem service)",
    "R4": "sem ciclos entre pacotes de primeiro nível nem entre adaptadores",
    "R5": "adaptadores de entrada não acessam repositórios, serviço, saída, Spring Data nem JPA",
}


@dataclass
class Resultado:
    violacoes: int
    por_regra: dict[str, int]
    fonte: str  # archunit | estatica
    detalhes: list[str]

    @property
    def regras_violadas(self) -> int:
        return sum(1 for v in self.por_regra.values() if v > 0)


def verificar_estaticamente(p: Projeto, usar_jdeps: bool = True) -> Resultado:
    por = dict.fromkeys(REGRAS, 0)
    det: list[str] = []

    def registra(regra, arquivo, texto):
        por[regra] += 1
        det.append(f"{regra} {arquivo.caminho.relative_to(p.raiz)}: {texto}")

    def sob(pacote, *prefixo):
        return relativo(pacote, p.pacote_base)[: len(prefixo)] == list(prefixo)

    for a in p.arquivos:
        orig = camada(a.pacote, p.pacote_base)
        for imp in a.imports:
            dest_pacote = pacote_do_import(imp, p)
            dest = camada(dest_pacote, p.pacote_base) if dest_pacote else None
            externo = dest_pacote is None
            if orig == "domain" and ((not externo and dest != "domain") or (externo and not imp.startswith("java."))):
                registra("R1", a, f"importa {imp}")
            if orig == "application" and ((not externo and dest not in ("domain", "application")) or (externo and not imp.startswith("java."))):
                registra("R2", a, f"importa {imp}")
            if (orig == "entrada" and dest == "saida") or (
                orig == "saida" and (dest == "entrada" or (dest_pacote and (sob(dest_pacote, "application", "port", "in") or sob(dest_pacote, "application", "service"))))
            ):
                registra("R3", a, f"importa {imp}")
            if orig == "entrada" and (
                dest == "saida"
                or (dest_pacote and (sob(dest_pacote, "application", "port", "out") or sob(dest_pacote, "application", "service")))
                or imp.startswith(("org.springframework.data", "jakarta.persistence", "javax.persistence"))
            ):
                registra("R5", a, f"importa {imp}")
    grafo, _ = dependencias(p, usar_jdeps)
    por["R4"] = ciclos(grafo_de_modulos(grafo, p.pacote_base))
    if por["R4"]:
        det.append(f"R4 {por['R4']} ciclo(s) entre pacotes")
    return Resultado(sum(por.values()), por, "estatica", det)


_RE_VIOLADA = re.compile(r"was violated \((\d+) times?\)")


def contar_violacoes_archunit(texto: str) -> int:
    """Soma o 'N times' de cada regra violada nos relatórios do surefire/ArchUnit."""
    return sum(int(n) for n in _RE_VIOLADA.findall(texto))


def verificar_com_archunit(raiz: Path, teste: str = "ArchitectureTest", mvn: str = "mvn") -> Resultado | None:
    """Roda o teste ArchUnit da semente e soma as violações. None se o Maven não existe."""
    try:
        subprocess.run([mvn, "-q", "-B", "test", f"-Dtest={teste}", "-DfailIfNoTests=false"], cwd=raiz, capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        return None
    textos = [f.read_text(errors="replace") for f in (raiz / "target" / "surefire-reports").glob(f"*{teste}*") if f.suffix in (".txt", ".xml")]
    if not textos:
        return None
    # o .txt e o .xml repetem a mesma mensagem: usa só o .txt quando houver
    txt = [t for t, f in zip(textos, (raiz / "target" / "surefire-reports").glob(f"*{teste}*")) if f.suffix == ".txt"]
    total = contar_violacoes_archunit("\n".join(txt or textos))
    return Resultado(total, {}, "archunit", [])


def medir(p: Projeto, usar_archunit: bool = True, usar_jdeps: bool = True) -> Resultado:
    if usar_archunit:
        r = verificar_com_archunit(p.raiz)
        if r is not None:
            estatico = verificar_estaticamente(p, usar_jdeps)
            r.por_regra = estatico.por_regra  # mantém o detalhe por regra para a deriva documental
            r.detalhes = estatico.detalhes
            return r
    return verificar_estaticamente(p, usar_jdeps)
