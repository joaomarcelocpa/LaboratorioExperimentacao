# Hipóteses e Validação — RQ04 e RQ05

## Hipótese informal

**RQ04 (frequência de atualização):** Acreditamos que repositórios populares sejam ativamente mantidos, com última atualização recente — mediana de no máximo alguns dias —, pois projetos com muitas estrelas tendem a atrair contribuidores e mantenedores que mantêm o código em constante evolução.

**RQ05 (linguagem primária):** Esperamos que linguagens de propósito geral e alta adoção no mercado — como Python e JavaScript/TypeScript — dominem a lista, já que são as mais usadas pela comunidade open source e favorecem maior quantidade de contribuidores.

## Validação

- [x] Calcular mediana de `atualizado_em` (convertida em dias desde a atualização)
- [x] Identificar valores ausentes
- [x] Identificar outliers em `atualizado_em`
- [x] Contar distribuição de `linguagem`

**Metodologia:** cálculo feito com o script [`scripts/validador-bernardo.py`](../../scripts/validador-bernardo.py) sobre `dados/repositorios.csv` (1000 repositórios); outliers detectados pelo método IQR (1.5×IQR); percentuais calculados sobre o total de 1000 repositórios.

## Resultados

### RQ04 — Frequência de atualização (`atualizado_em`)

| RQ | Coluna | Valores ausentes | Total de linhas | Média (dias) | Mediana (dias) | Qtd. outliers |
|----|--------|:---:|:---:|:---:|:---:|:---:|
| RQ04 | `atualizado_em` | 0 | 1000 | 1.11 | **1.0** | 99 |

**RQ04 — `atualizado_em`:** a mediana de 1 dia desde a última atualização confirma a hipótese: repositórios populares são atualizados com altíssima frequência. A média (1,11 dias) praticamente coincide com a mediana, o que indica distribuição concentrada próxima de zero — a grande maioria dos repositórios foi atualizada no próprio dia ou no dia anterior à coleta. Os 99 outliers (9,9% da amostra) representam repositórios com atualização mais distante, mas ainda assim são minoria.

### RQ05 — Linguagem primária (`linguagem`)

| Posição | Linguagem | Quantidade | % |
|:---:|---|:---:|:---:|
| 1 | Python | 229 | 22,9% |
| 2 | TypeScript | 174 | 17,4% |
| 3 | JavaScript | 111 | 11,1% |
| 4 | Go | 76 | 7,6% |
| 5 | Rust | 57 | 5,7% |
| 6 | Java | 41 | 4,1% |
| 7 | C++ | 40 | 4,0% |
| 8 | Jupyter Notebook | 24 | 2,4% |
| 9 | C | 21 | 2,1% |
| 10 | Shell | 20 | 2,0% |
| — | Demais (32 linguagens) | 120 | 12,0% |
| — | (sem linguagem) | 87 | 8,7% |

**RQ05 — `linguagem`:** Python lidera com 22,9%, seguido de TypeScript (17,4%) e JavaScript (11,1%), confirmando a hipótese. As três juntas somam 51,4% da amostra. Go e Rust surgem em 4º e 5º lugar, refletindo o crescimento de linguagens compiladas de alta performance no ecossistema open source. Os 87 repositórios sem linguagem definida (8,7%) correspondem principalmente a repositórios de documentação, configuração ou recursos mistos.
