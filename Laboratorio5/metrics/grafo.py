"""Grafo de dependências entre pacotes e ciclos.

Fonte preferida: jdeps sobre as classes compiladas (grafo de bytecode).
Alternativa: imports dos fontes, que dá o mesmo grafo de pacotes em projetos
sem classes compiladas. O resultado diz qual fonte foi usada.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from metrics.java import Projeto, pacote_do_import


def grafo_dos_fontes(p: Projeto) -> dict[str, set[str]]:
    g: dict[str, set[str]] = {pk: set() for pk in p.pacotes}
    for a in p.arquivos:
        for imp in a.imports:
            dest = pacote_do_import(imp, p)
            if dest and dest != a.pacote:
                g[a.pacote].add(dest)
    return g


_RE_ARESTA = re.compile(r'"([^"]+)"\s*->\s*"([^"]+?)(?:\s*\([^)]*\))?"\s*;')


def grafo_do_jdeps(classes: Path, pacote_base: str, jdeps: str = "jdeps") -> dict[str, set[str]]:
    """Roda `jdeps -verbose:package -dotoutput` e devolve só arestas internas ao pacote-base."""
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [jdeps, "-verbose:package", "-filter:none", "-dotoutput", tmp, str(classes)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"jdeps falhou: {r.stderr.strip() or r.stdout.strip()}")
        g: dict[str, set[str]] = {}
        for dot in Path(tmp).glob("*.dot"):
            if dot.name == "summary.dot":
                continue
            for origem, destino in _RE_ARESTA.findall(dot.read_text()):
                if pacote_base and not (origem.startswith(pacote_base) and destino.startswith(pacote_base)):
                    continue
                g.setdefault(origem, set())
                g.setdefault(destino, set())
                if origem != destino:
                    g[origem].add(destino)
        return g


def componentes_ciclicos(g: dict[str, set[str]]) -> list[list[str]]:
    """Componentes fortemente conexos com mais de um pacote (Tarjan iterativo)."""
    indice, baixo, pilha, na_pilha, resultado = {}, {}, [], set(), []
    contador = 0
    for raiz in sorted(g):
        if raiz in indice:
            continue
        trabalho = [(raiz, iter(sorted(g.get(raiz, ()))))]
        indice[raiz] = baixo[raiz] = contador
        contador += 1
        pilha.append(raiz)
        na_pilha.add(raiz)
        while trabalho:
            no, filhos = trabalho[-1]
            avancou = False
            for f in filhos:
                if f not in indice:
                    indice[f] = baixo[f] = contador
                    contador += 1
                    pilha.append(f)
                    na_pilha.add(f)
                    trabalho.append((f, iter(sorted(g.get(f, ())))))
                    avancou = True
                    break
                if f in na_pilha:
                    baixo[no] = min(baixo[no], indice[f])
            if avancou:
                continue
            trabalho.pop()
            if trabalho:
                pai = trabalho[-1][0]
                baixo[pai] = min(baixo[pai], baixo[no])
            if baixo[no] == indice[no]:
                comp = []
                while True:
                    w = pilha.pop()
                    na_pilha.remove(w)
                    comp.append(w)
                    if w == no:
                        break
                if len(comp) > 1:
                    resultado.append(sorted(comp))
    return resultado


def ciclos(g: dict[str, set[str]]) -> int:
    """Número de ciclos = componentes fortemente conexos com mais de um pacote."""
    return len(componentes_ciclicos(g))


def classes_compiladas(raiz: Path) -> Path | None:
    for c in (raiz / "target" / "classes", raiz / "build" / "classes" / "java" / "main"):
        if c.is_dir() and any(c.rglob("*.class")):
            return c
    return None


def dependencias(p: Projeto, usar_jdeps: bool = True) -> tuple[dict[str, set[str]], str]:
    """(grafo, fonte) com fonte = 'jdeps' ou 'fontes'."""
    classes = classes_compiladas(p.raiz) if usar_jdeps else None
    if classes:
        try:
            return grafo_do_jdeps(classes, p.pacote_base), "jdeps"
        except (RuntimeError, FileNotFoundError):
            pass
    return grafo_dos_fontes(p), "fontes"
