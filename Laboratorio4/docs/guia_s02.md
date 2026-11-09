# Guia da Sprint 2 (Lab 04)

Esta é a última sprint: ela fecha as simulações, o dashboard completo e a apresentação oral. Leia este guia antes de começar sua Issue.

## 1. Onde estamos

A Sprint 1 entregou os dados reais (`data/raw/prs.csv`), o cenário (`docs/cenario.md`), o gerador lognormal e o G1 (`src/gerador.py`), os dois testes aplicados a um conjunto simulado (`src/testes.py`, `docs/interpretacao_s01.md`), o G2 (`src/g2.py`) e o esqueleto do dashboard (`app.py`).

Decisões que continuam valendo:

| Item | Decisão |
|---|---|
| Par de testes | t de Welch (médias) × Mann-Whitney (postos) |
| Teste | Bicaudal, α = 0,05 |
| Variável | `horas_ate_merge` |
| Repetições | 10.000 por cenário |
| Semente | `numpy.random.default_rng(42)` |
| Cores dos gráficos | as de `src/gerador.py` (`CORES`), a mesma cor por teste em todos os gráficos |

## 2. As três perguntas da simulação

- **Q1, erro tipo I:** sem diferença entre os grupos, com que frequência cada teste rejeita H₀? O esperado é perto de 5%.
- **Q2, poder:** com diferença real, com que frequência cada teste a detecta? Pelo menos 5 tamanhos de efeito, começando em zero.
- **Q3, dados mal-comportados:** repetir Q1 e Q2 em pelo menos uma situação que viole os pressupostos do t de Welch (mais assimetria, outliers ou amostra pequena).

## 3. O motor de simulação (`src/simulacao.py`)

Já está pronto. Todo mundo usa a mesma função, para os resultados serem comparáveis:

```python
from src.simulacao import simular

simular(n=30, razao_medianas=2.0, sigma=2.5225, repeticoes=10_000, seed=42)
# {'welch': 0.0331, 'mann_whitney': 0.165}
```

| Parâmetro | Significado |
|---|---|
| `n` | observações por grupo |
| `razao_medianas` | mediana do grupo B ÷ mediana do grupo A. **1 = sem efeito (H₀ verdadeira)**. É o tamanho do efeito |
| `sigma` | σ do log nos dois grupos. Maior = mais assimétrico, com cauda mais longa |
| `repeticoes` | número de conjuntos simulados |

A função devolve a **proporção de p < 0,05** de cada teste. Com `razao_medianas=1` é o erro tipo I. Com `razao_medianas > 1` é o poder.

Os dois grupos partem de uma referência comum (média dos parâmetros reais dos dois grupos: μ = 2,127 e σ = 2,5225). O efeito é aplicado deslocando o μ do log do grupo B em `ln(razão)`. Sugestão de tamanhos de efeito: **1, 1,5, 2, 3 e 5** (nos dados reais a razão das medianas é cerca de 2,5).

### Resultado de Q1 (já calculado)

`python -m src.simulacao` salva `data/simulated/q1_erro_tipo_i.csv`:

| Teste | Erro tipo I | Margem (95%) |
|---|---|---|
| t de Welch | 1,41% | ± 0,23 p.p. |
| Mann-Whitney | 4,74% | ± 0,42 p.p. |

O Welch fica bem **abaixo** de 5% (conservador) e o Mann-Whitney fica perto de 5%. Isso responde à pergunta 9 da apresentação (quem se afastou de 5%, e se ficou liberal ou conservador), e o grupo precisa explicar o porquê: com cauda longa, a variância da média fica muito grande e o teste t quase nunca atinge o valor crítico.

### Resultados preliminares de poder (referência, n = 30)

| Razão das medianas | Welch | Mann-Whitney |
|---|---|---|
| 1,0 | 1,4% | 4,7% |
| 1,5 | 2,1% | 8,6% |
| 2,0 | 3,3% | 16,5% |
| 3,0 | 6,7% | 36,0% |
| 5,0 | 12,8% | 65,3% |

## 4. As Issues da Sprint 2

| Issue | Tarefa | Quem | Depende de |
|---|---|---|---|
| #94 | Motor de simulação e Q1 | João | Pronto |
| #95 | Dashboard: seção 6, esqueleto das seções 4 e 5, README | João | Nada |
| #96 | Q2: poder no cenário base | Bernardo | #94 |
| #97 | Dashboard: seções 4, 5 e 7 e roteiro das 15 perguntas | Bernardo | #96, #98, #99 |
| #98 | Q3: situações que violam os pressupostos | Miguel | #94 |
| #99 | G3 e G4 | Miguel | #96, #98 |
| #100 | Bônus: gráfico interativo de poder | João | #94 |

### Bernardo
- **#96 (Q2):** chame `simular` para cada `razao_medianas` (pelo menos 5, começando em 1) e salve a tabela em `data/simulated/q2_poder.csv`, com as colunas `razao_medianas`, `teste` e `poder`.
- **#97:** com G3 e G4 prontos, escreva os textos das seções 4 e 5 (2 a 4 frases), a conclusão da seção 7 e o `docs/roteiro.md`. Na conclusão, compare o resultado com o **palpite que você escreveu em `docs/cenario.md`** (pergunta 13).

### Miguel
- **#98 (Q3):** escolha pelo menos uma situação ruim e rode Q1 e Q2 nela com `simular`. Dicas: `sigma` maior deixa os dados mais assimétricos, e `n` pequeno (por exemplo 10) testa amostras pequenas. Salve em `data/simulated/q3_situacoes.csv`, com as colunas `situacao`, `razao_medianas`, `teste` e `taxa`.
- **#99 (G3 e G4):** G3 mostra o erro tipo I por situação (Q1 e Q3), com linha em 5%. G4 mostra as curvas de poder dos dois testes no mesmo gráfico (Q2 e Q3). Título, eixos com nome e unidade, legenda e as cores de `CORES`.

### João
- **#95:** tabela da seção 6 (dados reais), espaço de G3 e G4 e README com o comando único.
- **#100 (bônus):** aba interativa com `n` e `razao_medianas` ajustáveis. Use menos repetições para responder rápido.

## 5. Ordem de trabalho

1. O motor (#94) está pronto: Bernardo e Miguel já podem começar a #96 e a #98.
2. João faz a #95 em paralelo.
3. Miguel faz os gráficos (#99) quando a #96 e a #98 terminarem.
4. Bernardo escreve os textos e a conclusão (#97) com os gráficos prontos.
5. Todos ensaiam as 15 perguntas.

## 6. Regras

- **Todo commit cita o número da Issue**, por exemplo `Q3 com sigma maior (#98)`. Commits sem referência não contam.
- Cada integrante é Assignee de ao menos uma Issue com código commitado.
- Mantenha o cartão no Kanban atualizado e feche a Issue ao terminar.
- Ambiente: `source .venv/bin/activate` e `pip install -r requirements.txt`.
- Testes: `python -m pytest`.
