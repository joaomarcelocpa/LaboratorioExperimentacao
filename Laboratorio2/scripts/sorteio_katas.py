import json
import random

SEED = 42
ARQUIVO_KATAS = "katas.json"


def carregar_katas(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return dados["katas"], dados["integrantes"]


def agrupar_por_dificuldade(katas):
    grupos = {}
    for kata in katas:
        grupos.setdefault(kata["dificuldade"], []).append(kata)
    for dificuldade, lista in grupos.items():
        if len(lista) != 2:
            raise ValueError(
                f"Esperado exatamente 2 katas para a dificuldade '{dificuldade}', "
                f"encontrado {len(lista)}. Ajuste o katas.json."
            )
    return grupos


def sortear_distribuicao(katas, integrantes, seed=SEED):
    random.seed(seed)
    grupos = agrupar_por_dificuldade(katas)

    distribuicao = {integrante: {"com_ia": [], "sem_ia": []} for integrante in integrantes}

    for dificuldade, par in grupos.items():
        for integrante in integrantes:
            kata_a, kata_b = par
            if random.random() < 0.5:
                com_ia, sem_ia = kata_a, kata_b
            else:
                com_ia, sem_ia = kata_b, kata_a

            distribuicao[integrante]["com_ia"].append(com_ia["id"])
            distribuicao[integrante]["sem_ia"].append(sem_ia["id"])

    return distribuicao


def imprimir_tabela(distribuicao, katas):
    katas_por_id = {kata["id"]: kata for kata in katas}

    for integrante, grupos in distribuicao.items():
        print(f"\nIntegrante {integrante}")
        print("-" * 60)
        print("  Com IA:")
        for kata_id in grupos["com_ia"]:
            kata = katas_por_id[kata_id]
            print(f"    [{kata['dificuldade']:<8}] {kata_id} - {kata['nome']}")
        print("  Sem IA:")
        for kata_id in grupos["sem_ia"]:
            kata = katas_por_id[kata_id]
            print(f"    [{kata['dificuldade']:<8}] {kata_id} - {kata['nome']}")


if __name__ == "__main__":
    katas, integrantes = carregar_katas(ARQUIVO_KATAS)
    distribuicao = sortear_distribuicao(katas, integrantes)
    imprimir_tabela(distribuicao, katas)