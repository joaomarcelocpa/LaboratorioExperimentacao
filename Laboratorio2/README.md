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

Foram selecionados 6 katas do LeetCode (3 fáceis e 3 médios), priorizando baixo número de
resoluções (`Accepted`) e tags mais específicas, com o objetivo de reduzir o risco de a IA
(ou o próprio integrante) já conhecer a solução de memória.

| ID | Kata | Nº LeetCode | Dificuldade | Link |
|----|------|-------------|-------------|------|
| F1 | Final Value of Variable After Performing Operations | 2011 | Fácil | https://leetcode.com/problems/final-value-of-variable-after-performing-operations/ |
| F2 | Find Winner on a Tic Tac Toe Game | 1275 | Fácil | https://leetcode.com/problems/find-winner-on-a-tic-tac-toe-game/ |
| F3 | Count Prefixes of a Given String | 2255 | Fácil | https://leetcode.com/problems/count-prefixes-of-a-given-string/ |
| M1 | Additive Number | 306 | Média | https://leetcode.com/problems/additive-number/ |
| M2 | Maximum Binary Tree | 654 | Média | https://leetcode.com/problems/maximum-binary-tree/ |
| M3 | Least Number of Unique Integers after K Removals | 1481 | Média | https://leetcode.com/problems/least-number-of-unique-integers-after-k-removals/ |

Os katas difíceis usados na versão anterior do desenho (Longest Cycle in a Graph — #2360 e
Longest Path With Different Adjacent Characters — #2246) foram removidos. No lugar deles,
entraram um novo kata fácil (F3) e um novo kata médio (M3).

A lista estruturada está versionada em `katas.json`.

## 6. Tipo de projeto experimental

Os 6 katas foram agrupados em **3 pares** (cada par contendo 1 kata fácil + 1 kata médio):
Par X, Par Y e Par Z.

O desenho adota um **rodízio contrabalanceado entre o trio**: cada integrante resolve um par
manualmente e outro par com IA, de forma que cada par acabe sendo resolvido **uma vez na mão
e uma vez com IA**, sempre por integrantes diferentes:

| Integrante | Na mão | Com IA |
|---|---|---|
| A | Par X | Par Y |
| B | Par Z | Par X |
| C | Par Y | Par Z |

Cada integrante realiza, portanto, **4 trials** (2 na mão + 2 com IA) em vez dos 6 do desenho
anterior. Continua sendo um desenho **within-subject** no sentido de que cada integrante
passa pelos dois tratamentos (com e sem IA) — mas o tratamento não é mais aplicado sobre o
mesmo conjunto de katas para a mesma pessoa: cada kata é resolvido por uma pessoa na mão e
por outra pessoa diferente com IA.

Essa mudança substitui o desenho anterior (cada integrante resolvendo todos os 6 katas), que
apresentava uma limitação: com apenas 2 katas por dificuldade e 3 integrantes, pelo menos
dois integrantes acabavam repetindo a mesma combinação de tratamento por dificuldade,
tornando a divisão desproporcional entre katas. O rodízio por pares resolve isso: cada kata
é sempre testado exatamente uma vez em cada tratamento, nunca duas vezes no mesmo.

## 7. Quantidade de medições

6 katas × 2 tratamentos (mão/IA) = **12 trials no total**, sendo 6 com IA e 6 sem IA
(cada kata é resolvido exatamente uma vez em cada tratamento). Cada integrante realiza
4 trials (2 na mão + 2 com IA).

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

- **Diferença de habilidade individual entre integrantes**: como cada kata é resolvido na
  mão por uma pessoa e com IA por outra pessoa diferente (rodízio entre o trio), a
  comparação entre tratamentos deixa de ser 100% controlada pela habilidade individual —
  diferente de um desenho onde a mesma pessoa resolve o mesmo kata nos dois tratamentos.
  Uma eventual diferença de desempenho entre integrantes pode se misturar ao efeito da IA.
  Essa é uma limitação assumida em troca de uma divisão proporcional entre os tratamentos
  (cada kata testado exatamente uma vez em cada tratamento).
- **Efeito de aprendizado**: como cada integrante resolve 4 katas ao longo do experimento, é
  possível que fique mais rápido nos últimos simplesmente por prática, e não por causa da IA.
  Mitigado parcialmente pela ordem contrabalanceada entre integrantes.
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
- **Assistente de IA**: Claude (versão gratuita)
- **Ferramenta de métricas estáticas**: Radon (`cc`, `mi`, `raw`)
- **Scripts de apoio**: `sortear_distribuicao.py` (a ser ajustado para o novo esquema de
  rodízio por pares), script de cronometragem (Issue #24) e script de métricas (Issue #25)