"""
Arquivo de exemplo para testar o script de métricas Radon.
Contém funções com diferentes complexidades ciclomáticas.
"""


def soma(a, b):
    return a + b


def classifica_nota(nota):
    if nota >= 90:
        return "A"
    elif nota >= 80:
        return "B"
    elif nota >= 70:
        return "C"
    elif nota >= 60:
        return "D"
    else:
        return "F"


def fatorial(n):
    if n < 0:
        raise ValueError("n deve ser não-negativo")
    resultado = 1
    for i in range(2, n + 1):
        resultado *= i
    return resultado


def busca_binaria(lista, alvo):
    esquerda, direita = 0, len(lista) - 1
    while esquerda <= direita:
        meio = (esquerda + direita) // 2
        if lista[meio] == alvo:
            return meio
        elif lista[meio] < alvo:
            esquerda = meio + 1
        else:
            direita = meio - 1
    return -1


class Calculadora:
    def __init__(self):
        self.historico = []

    def calcular(self, op, a, b):
        if op == "+":
            resultado = a + b
        elif op == "-":
            resultado = a - b
        elif op == "*":
            resultado = a * b
        elif op == "/":
            if b == 0:
                raise ZeroDivisionError("Divisão por zero")
            resultado = a / b
        else:
            raise ValueError(f"Operação inválida: {op}")
        self.historico.append((op, a, b, resultado))
        return resultado
