# Codificação das decisões do Claude Code

Base: PLANEJAMENTO.pdf, seções 3.9 e 4.1. Issue: #114.

> **Status:** aguardando transcripts da coleta completa. Este documento descreve o método,
> a amostra e registrará os resultados quando os dados estiverem disponíveis.

---

## 1. Amostra a codificar

**Escopo:** todos os commits gerados pelo agente na coleta completa (modo incremental e
modo regenerado), exceto passos censurados (`run_ok=0`).

**Estratificação:** a amostra de calibração (~20% dos commits, mínimo 20 itens) é sorteada
com proporções iguais entre:
- Modo incremental × Modo regenerado
- Tipo de pedido: "cabe" × "tensiona"

**Semente do sorteio:** 7 (fixa, registrada antes de abrir os dados).

**Justificativa:** todos os commits são codificados (não só amostra) para a análise qualitativa
completa. A amostra estratificada é usada apenas para a calibração e cálculo de kappa.

---

## 2. Definição operacional de "decisão" para fins de codificação

Ver `docs/s02/livro-de-codigos.md`, seção "O que é uma decisão".

---

## 3. Resultados da calibração

> _A preencher após a calibração entre os dois avaliadores (antes de codificar os dados completos)._

### 3.1 Amostra de calibração

| Item | Valor |
|---|---|
| Commits sorteados (calibração) | `_a preencher_` |
| Semente usada | 7 |
| Data da calibração | `_a preencher_` |

### 3.2 Kappa de Cohen por categoria

| Categoria | Kappa | Interpretação | Decisão |
|---|---|---|---|
| LOC | `_a preencher_` | — | — |
| EST-C | `_a preencher_` | — | — |
| EST-I | `_a preencher_` | — | — |
| TST | `_a preencher_` | — | — |
| DOC | `_a preencher_` | — | — |

### 3.3 Tabela de discordâncias

| Commit | Categoria | Código avaliador A | Código avaliador B | Resolução |
|---|---|---|---|---|
| `_a preencher_` | — | — | — | — |

### 3.4 Ajustes feitos no livro de códigos após calibração

`_A preencher: quais definições ou exemplos foram ajustados, se houver._`

---

## 4. Codificação completa — avaliador A (@bernardordm)

> _A preencher após a calibração concluída. O CSV do avaliador A está em
> `results/codificacao/avaliador-A.csv`._

**Período da codificação:** `_a preencher_`
**Número de commits codificados:** `_a preencher_`

---

## 5. Resultado final (pós-reconciliação)

> _A preencher após a reconciliação com o avaliador B._

**Kappa final (pós-resolução):** `_a preencher_`
**Distribuição dos códigos:** `_a preencher com tabela de frequências por categoria_`
