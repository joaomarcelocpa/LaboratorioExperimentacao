# Hipóteses e Validação — RQ01, RQ02 e RQ03

## Hipótese informal

**RQ01 (idade dos repositórios):** Acreditamos que repositórios populares sejam maduros, com idade média acima de 8 anos, já que construir uma base de milhares de estrelas normalmente leva tempo.

**RQ02 (PRs mergeadas):** Esperamos um volume alto de contribuições aceitas, pois projetos populares atraem colaboradores externos e mantenedores ativos, gerando um ciclo constante de contribuição da comunidade.

**RQ03 (releases):** Esperamos releases frequentes nos repositórios populares, refletindo manutenção ativa e um ciclo constante de entrega de novas versões.

## Validação

- [x] Calcular mediana de `criado_em`, `prs_mergeadas` e `releases`
- [x] Identificar valores ausentes
- [x] Identificar outliers

**Metodologia:** cálculo feito com o script [`scripts/validador-joao.py`](../../scripts/validador-joao.py) sobre `dados/repositorios.csv` (1000 repositórios) e outliers detectados pelo método IQR (1.5×IQR).

## Resultados

| RQ | Coluna | Valores ausentes | Total de linhas | Média | Mediana | Qtd. outliers |
|----|--------|:---:|:---:|:---:|:---:|:---:|
| RQ01 | `criado_em` | 0 | 1000 | 2018-12-21 | **2018-11-24** | 0 |
| RQ02 | `prs_mergeadas` | 0 | 1000 | 4216.08 | **768.0** | 123 |
| RQ03 | `releases` | 0 | 1000 | 127.39 | **39.5** | 92 |

**RQ01 — `criado_em`:** a mediana de criação é 2018-11-24, o que corresponde a uma idade mediana de aproximadamente **7,7 anos** (data de referência: 2026-08-18). O valor fica **abaixo** do limiar de 8 anos previsto na hipótese — os repositórios são maduros, mas ligeiramente mais jovens do que o esperado. Não há valores ausentes nem outliers nesta coluna (o que é esperado, já que toda entrada tem uma data de criação válida).

**RQ02 — `prs_mergeadas`:** mediana de 768 PRs mergeadas por repositório, confirmando a hipótese de alto volume de contribuições aceitas. A média (4216,08) é bem mais alta que a mediana, indicando distribuição assimétrica puxada por poucos repositórios com volumes muito altos — coerente com os 123 outliers identificados (12,3% da amostra).

**RQ03 — `releases`:** mediana de 39,5 releases por repositório, sugerindo manutenção ativa e ciclo de entrega recorrente, alinhado com a hipótese. Assim como em RQ02, a média (127,39) muito acima da mediana e os 92 outliers indicam forte assimetria, com um grupo pequeno de projetos com número de releases muito acima do típico.
