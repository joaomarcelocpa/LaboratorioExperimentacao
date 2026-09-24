from pathlib import Path

from metricas_loc import classificar_arquivo

RAIZ = Path(__file__).parent.parent


def _escrever(tmp_path, codigo):
    caminho = tmp_path / "exemplo.py"
    caminho.write_text(codigo, encoding="utf-8")
    return caminho


def test_import_conta_como_diretiva(tmp_path):
    codigo = """from typing import List

def f(x):
    return x
"""
    r = classificar_arquivo(_escrever(tmp_path, codigo))
    assert r["loc_diretivas"] == 1
    assert r["loc_decl"] == 1  # "def f(x):"
    assert r["loc_exec"] == 1  # "return x"


def test_assinatura_de_classe_e_metodo_conta_como_declarativa(tmp_path):
    codigo = """class Solution:
    def resolver(self, nums):
        total = 0
        for n in nums:
            total += n
        return total
"""
    r = classificar_arquivo(_escrever(tmp_path, codigo))
    assert r["loc_decl"] == 2  # "class Solution:" + "def resolver(...):"
    assert r["loc_exec"] == 4  # total=0, for, total+=n, return
    assert r["loc_diretivas"] == 0


def test_anotacao_sem_valor_e_declarativa_mas_com_valor_e_executavel(tmp_path):
    codigo = """x: int
y: int = 5
"""
    r = classificar_arquivo(_escrever(tmp_path, codigo))
    assert r["loc_decl"] == 1  # x: int
    assert r["loc_exec"] == 1  # y: int = 5 (executa a atribuição)


def test_branco_e_comentario_batem_com_radon(tmp_path):
    codigo = """# comentário
x = 1

y = 2
"""
    r = classificar_arquivo(_escrever(tmp_path, codigo))
    assert r["loc_branco"] == 1
    assert r["loc_comentario"] == 1
    assert r["loc_total"] == 4


def test_todos_os_katas_reais_toda_linha_e_classificada():
    """Confere a invariante: toda linha cai em branco/comentário/diretiva/
    decl/exec (nenhum kata atual tem decorador ou docstring solto — ver
    limitações no metricas_loc.py)."""
    for arquivo in sorted((RAIZ / "katas").rglob("*.py")):
        r = classificar_arquivo(arquivo)
        assert r["loc_nao_classificada"] == 0, arquivo
        assert r["loc_exec"] + r["loc_decl"] + r["loc_diretivas"] == r["ncloc"], arquivo
        assert r["ncloc"] + r["loc_branco"] + r["loc_comentario"] == r["loc_total"], arquivo
