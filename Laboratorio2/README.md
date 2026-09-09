# Desenho do Experimento — LAB02

## 1. Hipóteses

### RQ1 — Tempo
- **H0**: o tempo até passar em todos os testes de aceitação é igual, com ou sem uso de IA.
- **H1**: o uso de IA reduz o tempo até passar em todos os testes de aceitação.

### RQ2 — Defeitos
- **H0**: a taxa de testes de aceitação passando ao final do time-box é igual, com ou sem uso de IA.
- **H1**: o uso de IA aumenta a taxa de testes de aceitação passando ao final do time-box.

### RQ3 — Estrutura do código
- **H0**: a complexidade ciclomática e a duplicação do código produzido são iguais, com ou sem uso de IA.
- **H1**: o uso de IA altera a complexidade ciclomática e/ou a duplicação do código produzido.

## 2. Variável independente

Uso ou não de assistente de IA (Claude) durante a resolução do kata.

## 3. Variáveis dependentes

- Tempo até passar em todos os testes de aceitação ("time-to-green"), em minutos.
- Taxa de testes de aceitação passando ao final do time-box (%).
- Complexidade ciclomática média por função (Radon `cc`).
- Duplicação de código.
- LOC (linhas de código) — métrica de controle, usada para normalizar as métricas acima.

## 4. Tratamentos

- **Com IA**: o integrante resolve o kata com o assistente de IA (Claude) habilitado.
- **Sem IA**: o integrante resolve o kata sem nenhuma assistência externa (ver regra na seção 8).

## 5. Objetos experimentais (katas)

Foram selecionados 6 katas do LeetCode, priorizando baixo número de resoluções (`Accepted`) e
tags mais específicas, com o objetivo de reduzir o risco de a IA (ou o próprio integrante)
já conhecer a solução de memória.

| ID | Kata | Nº LeetCode | Dificuldade | Link |
|----|------|-------------|-------------|------|
| F1 | Final Value of Variable After Performing Operations | 2011 | Fácil | https://leetcode.com/problems/final-value-of-variable-after-performing-operations/ |
| F2 | Find Winner on a Tic Tac Toe Game | 1275 | Fácil | https://leetcode.com/problems/find-winner-on-a-tic-tac-toe-game/ |
| M1 | Additive Number | 306 | Média | https://leetcode.com/problems/additive-number/ |
| M2 | Maximum Binary Tree | 654 | Média | https://leetcode.com/problems/maximum-binary-tree/ |
| D1 | Longest Cycle in a Graph | 2360 | Difícil | https://leetcode.com/problems/longest-cycle-in-a-graph/ |
| D2 | Longest Path With Different Adjacent Characters | 2246 | Difícil | https://leetcode.com/problems/longest-path-with-different-adjacent-characters/ |

A lista estruturada está versionada em `katas.json`.

## 6. Tipo de projeto experimental

Foi adotado um desenho **crossover / within-subject contrabalanceado**: cada integrante do
trio resolve todos os 6 katas, sendo 3 com IA e 3 sem IA. Para cada par de katas de mesma
dificuldade, um kata é resolvido com IA e o outro sem IA — nunca os dois no mesmo tratamento.
Essa divisão foi sorteada de forma reprodutível pelo script `sortear_distribuicao.py`
(seed fixa), a partir do `katas.json`.

Esse desenho garante que cada integrante sirva de controle de si mesmo, eliminando a
variação individual de habilidade como fator de confusão na comparação entre tratamentos.

**Limitação conhecida**: como existem apenas 2 katas por faixa de dificuldade, e o trio tem
3 integrantes, o princípio da casa dos pombos garante que pelo menos dois integrantes
terão a mesma combinação (kata X com IA / kata Y sem IA) em pelo menos uma dificuldade.
O contrabalanceamento, portanto, não é perfeito, mas é o melhor possível dado o tamanho do
conjunto de katas.

## 7. Quantidade de medições

6 katas × 3 integrantes = **18 trials no total**, sendo 9 com IA e 9 sem IA.

## 8. Regras de execução do trial

- Time-box fixo de **35 minutos** por trial.
- Se o integrante não passar em todos os testes dentro do tempo, o trial **não é descartado**:
  é registrado como censurado em 35 minutos, com o número de testes passando até aquele ponto
  (mesmo que seja zero).
- **Durante o trial "sem IA"**, não é permitido nenhum tipo de assistência externa: nem IA,
  nem tutoriais, nem soluções prontas do próprio kata, nem ajuda de terceiros. Consultar
  documentação oficial da linguagem é permitido; consultar a solução do problema não é.
  Essa regra existe para preservar a validade da comparação entre tratamentos.

## 9. Ameaças à validade

- **Efeito de aprendizado**: como cada integrante resolve 6 katas em sequência, é possível
  que fique mais rápido ao longo do experimento simplesmente por prática, e não por causa
  da IA. Mitigado parcialmente pela ordem contrabalanceada entre integrantes.
- **Familiaridade prévia com a ferramenta de IA**: integrantes que já usam o Claude no dia
  a dia podem ter vantagem no uso da ferramenta em si, independentemente da dificuldade do
  kata.
- **Risco de memorização/vazamento de solução**: mesmo priorizando katas pouco resolvidos,
  não é possível garantir com certeza que a IA não teve exposição a esses problemas durante
  o treinamento, nem que o integrante nunca os tenha visto antes. Essa é uma limitação
  reconhecida do experimento, mitigada — mas não eliminada — pela escolha de katas com baixo
  número de resoluções e fora das listas mais famosas (ex.: Top Interview 150, Blind 75).

## 10. Ambiente

- **Linguagem**: Python
- **Assistente de IA**: Claude Sonnet 5
- **Ferramenta de métricas estáticas**: Radon (`cc`, `mi`, `raw`)
- **Scripts de apoio**: `sortear_distribuicao.py` (distribuição dos katas), script de
  cronometragem (Issue #24) e script de métricas (Issue #25)