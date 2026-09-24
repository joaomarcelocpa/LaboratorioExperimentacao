"""
Classificação de LOC por tipo — Lab 2, Sprint 3, aprofundamento (além da
especificação, que só pede LOC total como métrica de controle).

Categorias, por linha física do arquivo:
  - LOC total       : todas as linhas do arquivo.
  - LOC em branco    : linhas vazias.
  - LOC comentário   : linhas cujo primeiro caractere não-espaço é `#`
    (comentário de linha inteira; comentário no fim de uma linha de código
    não conta aqui — a linha já é código, então entra na categoria do
    comando correspondente).
  - NCLOC            : total - branco - comentário.
  - LOC diretivas    : linhas de `import`/`from ... import`.
  - LOC declarativas : linha de assinatura de `class`/`def`, `global`/
    `nonlocal`, e anotação de tipo sem valor (`x: int`).
  - LOC executáveis  : as demais linhas de código (atribuições, retornos,
    chamadas, estruturas de controle) — é o "resto" do NCLOC depois de
    remover diretivas e declarativas.

Implementação: percorre a AST em ordem BFS (ast.walk visita nó pai antes dos
filhos) marcando o intervalo [lineno, end_lineno] de cada `import`/classe/
função/`global`/`nonlocal` com sua categoria; qualquer outro `ast.stmt` marca
seu intervalo como "executável". Como uma classe/função marca o próprio corpo
inteiro primeiro, e os comandos dentro do corpo são visitados depois (nível
mais profundo do BFS), a marcação dos filhos sobrescreve a dos pais nas linhas
que pertencem ao filho — sobra só a linha de assinatura como "declarativa".

Limitações conhecidas (nenhuma katas atual é afetada, mas documentado por
honestidade metodológica):
  - Linhas de decorador (`@algo`) não são classificadas (ficam de fora de
    todas as categorias) — nenhum kata usa decorador.
  - Docstrings/strings multi-linha usadas como comando (string literal solta)
    são classificadas como "executável" (tecnicamente Python as avalia e
    descarta), não como comentário — nenhum kata tem docstring.
"""

import ast
from pathlib import Path


def classificar_arquivo(caminho: Path) -> dict:
    codigo = caminho.read_text(encoding="utf-8", errors="replace")
    arvore = ast.parse(codigo)
    linhas = codigo.splitlines()
    total_linhas = len(linhas)
    rotulo = [None] * total_linhas

    # Marca branco/comentário PRIMEIRO e protege essas linhas contra
    # sobrescrita pela AST: uma linha em branco (ou só comentário) dentro do
    # corpo de uma função cai no intervalo [lineno, end_lineno] do FunctionDef
    # mesmo não sendo, ela própria, um comando — sem essa proteção ela seria
    # incorretamente herdada como "exec"/"decl" do bloco que a contém.
    for i, linha in enumerate(linhas):
        if not linha.strip():
            rotulo[i] = "branco"
        elif linha.lstrip().startswith("#"):
            rotulo[i] = "comentario"

    def marcar(node, categoria):
        inicio = node.lineno - 1
        fim = getattr(node, "end_lineno", node.lineno) - 1
        for i in range(inicio, fim + 1):
            if 0 <= i < total_linhas and rotulo[i] not in ("branco", "comentario"):
                rotulo[i] = categoria

    for node in ast.walk(arvore):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            marcar(node, "diretiva")
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            marcar(node, "decl")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            marcar(node, "decl")
        elif isinstance(node, ast.AnnAssign) and node.value is None:
            marcar(node, "decl")
        elif isinstance(node, ast.stmt):
            marcar(node, "exec")

    loc_branco = rotulo.count("branco")
    loc_comentario = rotulo.count("comentario")

    return {
        "arquivo": str(caminho),
        "loc_total": total_linhas,
        "loc_branco": loc_branco,
        "loc_comentario": loc_comentario,
        "ncloc": total_linhas - loc_branco - loc_comentario,
        "loc_diretivas": rotulo.count("diretiva"),
        "loc_decl": rotulo.count("decl"),
        "loc_exec": rotulo.count("exec"),
        # Deve ser sempre 0: toda linha cai em branco/comentário/diretiva/
        # decl/exec. Um valor > 0 indicaria decorador ou docstring solto
        # (ver limitações no docstring do módulo) — nenhum kata atual tem isso.
        "loc_nao_classificada": rotulo.count(None),
    }
