# Auditoria manual de saídas do Claude Code

Base: PLANEJAMENTO.pdf, seções 3.10 e 4.1. Issue: #115.

> **Status:** aguardando dados validados da coleta completa. Este documento descreve o
> protocolo e registrará os resultados quando os dados estiverem disponíveis.

> **Regra de protocolo:** o protocolo abaixo foi escrito **antes de olhar qualquer resultado**
> da coleta completa. Nenhuma mudança nos critérios de leitura é permitida após abrir os dados,
> exceto para corrigir ambiguidade com registro em `desvios.md`.

---

## 1. Objetivo

Verificar se os testes automatizados e as métricas do ArchUnit medem o que dizem medir,
usando leitura manual do diff e do código como padrão-ouro. Quantificar falsos positivos e
falsos negativos das métricas automáticas.

---

## 2. Protocolo de auditoria (escrito antes dos dados)

### 2.1 Seleção da amostra

- **Tamanho:** aproximadamente 20 saídas (commits do agente).
- **Sorteio:** semente fixa 13, estratificado por:
  - Modo: incremental × regenerado (10 de cada)
  - Tipo de pedido: "cabe" × "tensiona" (proporcional à distribuição na coleta)
- **Registro da amostra:** os IDs dos commits sorteados são registrados na seção 4 abaixo
  antes de qualquer leitura.

### 2.2 Critérios de leitura — o que verificar em cada saída

Para cada commit na amostra, responder **sim/não** a cada pergunta:

| Dimensão | Pergunta | Como verificar |
|---|---|---|
| Funcionalidade | O comportamento pedido está correto? | Ler o diff e comparar com o pedido correspondente |
| Regressão oculta | Existe regressão que os testes automáticos não pegaram? | Ler o diff procurando mudanças em código existente que podem quebrar comportamento anterior |
| Violação arquitetural oculta | Existe violação que o ArchUnit não flagou? | Verificar dependências no diff que violam as regras do `ARCHITECTURE.md` |
| Deriva documental | A deriva no `ARCHITECTURE.md` bate com o que o diff mostra? | Comparar diff do `ARCHITECTURE.md` (se houver) com as mudanças de código |

### 2.3 Resultado por saída

Cada saída recebe um veredito manual para cada dimensão:

| Veredito | Significado |
|---|---|
| OK | Nenhum problema na dimensão |
| PROBLEMA | Problema identificado (descrever) |
| INCONCLUSIVO | Não é possível determinar sem mais contexto |

### 2.4 Comparação com métricas automáticas

Após os vereditos manuais, comparar com as métricas automáticas:

| Resultado manual | Resultado automático | Classificação |
|---|---|---|
| PROBLEMA | Flagado | Verdadeiro positivo (TP) |
| OK | Não flagado | Verdadeiro negativo (TN) |
| PROBLEMA | Não flagado | Falso negativo (FN) — métrica perdeu |
| OK | Flagado | Falso positivo (FP) — métrica foi excessiva |

---

## 3. Amostra sorteada

> _A preencher antes de abrir os dados de cada saída. Registrar os IDs dos commits e a
> estratificação antes de iniciar qualquer leitura._

| Item | Valor |
|---|---|
| Semente | 13 |
| Total de saídas na coleta | `_a preencher_` |
| Saídas amostradas | `_a preencher_` |
| Data do sorteio | `_a preencher_` |

| # | Commit ID | Cadeia | Modo | Passo | Tipo de pedido |
|---|---|---|---|---|---|
| 1 | `_a preencher_` | — | — | — | — |
| ... | | | | | |

---

## 4. Resultados da auditoria

> _A preencher após a leitura manual. O CSV completo está em
> `results/auditoria/auditoria.csv`._

### 4.1 Concordância por dimensão

| Dimensão | TP | TN | FP | FN | Precisão | Recall |
|---|---|---|---|---|---|---|
| Regressão | `_a preencher_` | — | — | — | — | — |
| Violação arquitetural | `_a preencher_` | — | — | — | — | — |
| Deriva documental | `_a preencher_` | — | — | — | — | — |

### 4.2 Discordâncias relevantes

> _A preencher: casos em que o veredito manual divergiu da métrica automática e a discussão
> sobre o que causou a divergência._

| # | Commit | Dimensão | Manual | Automático | Discussão |
|---|---|---|---|---|---|
| 1 | `_a preencher_` | — | — | — | — |

### 4.3 Implicações para as ameaças à validade

> _A preencher: o que as discordâncias implicam para a validade de construto do estudo.
> Essas implicações devem ser refletidas em `docs/s02/ameacas-a-validade.md`._

---

## 5. Resumo para o relatório de análise

> _A preencher: 2-3 parágrafos resumindo o resultado da auditoria — taxa de concordância,
> principais fontes de discordância e o que isso significa para a interpretação dos resultados._
