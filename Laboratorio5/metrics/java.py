"""Leitura estática de um workspace Java: pacotes, imports e camadas.

Base comum dos scripts de métricas. Não executa nada do projeto: só lê os
arquivos de src/main/java.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DIR_FONTES = Path("src/main/java")

# Segmentos de pacote (abaixo do pacote-base) que identificam a camada.
SEG_DOMINIO = ("domain",)
SEG_APLICACAO = ("application",)
SEG_ENTRADA = ("web", "rest", "inbound", "input", "controller", "controllers", "api")
SEG_SAIDA = ("persistence", "outbound", "output", "jpa", "repository", "repositories", "db")
SEG_ADAPTADOR = ("adapter", "adapters")
PREFIXOS_FRAMEWORK = ("org.springframework", "jakarta.persistence", "javax.persistence", "org.hibernate")

_RE_PACOTE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
_RE_IMPORT = re.compile(r"^\s*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.M)
_RE_COMENTARIOS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


@dataclass
class ArquivoJava:
    caminho: Path
    pacote: str
    imports: list[str]  # nomes totalmente qualificados (sem o .* e sem static)
    nome: str  # nome do arquivo sem .java


@dataclass
class Projeto:
    raiz: Path
    pacote_base: str
    arquivos: list[ArquivoJava] = field(default_factory=list)

    @property
    def pacotes(self) -> set[str]:
        return {a.pacote for a in self.arquivos}


def ler_arquivo(caminho: Path) -> ArquivoJava | None:
    texto = _RE_COMENTARIOS.sub("", caminho.read_text(encoding="utf-8", errors="replace"))
    m = _RE_PACOTE.search(texto)
    if not m:
        return None
    imports = [i.group(2) for i in _RE_IMPORT.finditer(texto) if not i.group(1)]
    return ArquivoJava(caminho, m.group(1), imports, caminho.stem)


def pacote_base_comum(pacotes: set[str]) -> str:
    """Maior prefixo de pacote comum a todos (ex.: com.exemplo.tarefas)."""
    if not pacotes:
        return ""
    partes = [p.split(".") for p in pacotes]
    comum = []
    for segmentos in zip(*partes):
        if len(set(segmentos)) == 1:
            comum.append(segmentos[0])
        else:
            break
    # se só há um pacote, o prefixo comum é o próprio pacote: sobe um nível
    if len(pacotes) == 1 and comum:
        comum = comum[:-1]
    return ".".join(comum)


def carregar_projeto(raiz: Path, pacote_base: str | None = None) -> Projeto:
    raiz = Path(raiz)
    arquivos = []
    for f in sorted((raiz / DIR_FONTES).rglob("*.java")):
        a = ler_arquivo(f)
        if a:
            arquivos.append(a)
    base = pacote_base or pacote_base_comum({a.pacote for a in arquivos})
    return Projeto(raiz, base, arquivos)


def relativo(pacote: str, base: str) -> list[str]:
    if base and pacote == base:
        return []
    if base and pacote.startswith(base + "."):
        return pacote[len(base) + 1:].split(".")
    return pacote.split(".")


def camada(pacote: str, base: str) -> str:
    """domain | application | entrada | saida | outro, pelos segmentos abaixo do pacote-base."""
    seg = relativo(pacote, base)
    if not seg:
        return "outro"
    if seg[0] in SEG_DOMINIO:
        return "domain"
    if seg[0] in SEG_APLICACAO:
        return "application"
    if any(s in SEG_ENTRADA for s in seg):
        return "entrada"
    if any(s in SEG_SAIDA for s in seg):
        return "saida"
    return "outro"


def modulo(pacote: str, base: str) -> str:
    """Módulo = primeiro segmento abaixo do pacote-base; em adapter(s), os dois primeiros."""
    seg = relativo(pacote, base)
    if not seg:
        return "(raiz)"
    if seg[0] in SEG_ADAPTADOR and len(seg) > 1:
        return f"{seg[0]}.{seg[1]}"
    return seg[0]


def pacote_do_import(importado: str, projeto: Projeto) -> str | None:
    """Pacote interno ao qual o import pertence (None se for biblioteca externa)."""
    if projeto.pacote_base and not (importado == projeto.pacote_base or importado.startswith(projeto.pacote_base + ".")):
        return None
    conhecidos = projeto.pacotes
    candidato = importado
    while candidato:
        if candidato in conhecidos:
            return candidato
        candidato = candidato.rpartition(".")[0]
    return None
