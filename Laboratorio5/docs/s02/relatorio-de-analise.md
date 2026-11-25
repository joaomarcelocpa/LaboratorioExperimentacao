# Relatório de análise (S02)

Base: PLANEJAMENTO.pdf, seção 4.1. Issues: #126 (relatório), #123 (descritiva), #124 (modelos mistos), #125 (sobrevivência, diferença pareada e Holm).

> **Status: esqueleto.** Ainda não existe CSV da coleta completa (#119, #120). **Nenhum número deste documento é real.** As decisões de método (seções 2 e 3) estão escritas antes de olhar os dados e não mudam depois disso. Os resultados (seção 5) são preenchidos com os arquivos de `results/` gerados por script. Mudança de método depois de abrir os dados é registrada em `desvios.md`.

## Como gerar os números

```bash
python -m analysis.run --entrada data/coleta/passos.csv --saida results
```

| Pasta | Conteúdo | Seção |
|---|---|---|
| `results/descritiva/` | resumo da coleta, tabelas por modo e passo, cabe × tensiona | 5.1 e 5.2 |
| `results/figures/` | gráficos | 5.2 a 5.6 |
| `results/modelos/` | GLMM, GEE, GLMM com covariáveis, curvas de crescimento, H3, H5, diagnóstico | 5.3 e 5.4 |
| `results/sobrevivencia/` | Kaplan-Meier, log-rank e sensibilidade à censura | 5.5 |
| `results/diferenca-pareada/` | Wilcoxon pareado, delta de Cliff e IC | 5.6 |
| `results/testes_holm.csv` | família confirmatória com p e p de Holm | 5.7 |

Os números citados no texto precisam ser iguais aos dos arquivos. Para conferir, basta rodar o comando de novo sobre o mesmo CSV.

---

## 1. Perguntas e hipóteses

| Hipótese | Pergunta |
|---|---|
| H1 | A proporção de testes de regressão que falham cresce com o passo? |
| H2 | A localidade da mudança (arquivos e módulos tocados) e a duplicação pioram com o passo, mais no incremental? |
| H3 | As cadeias divergem mais umas das outras com o passo? |
| H4 | O modo incremental degrada mais que o regenerado no mesmo passo? |
| H5 | Pedidos que tensionam a arquitetura produzem mais regressões e violações novas que os que cabem? |

## 2. Decisões de método (fixadas antes dos dados)

O detalhamento está em `docs/s01/plano-de-analise.md`. Esta seção registra só o que foi decidido ou mudou na S02.

### 2.1 Pareamento da análise incremental × regenerado

O par é a **cadeia *i* incremental com a cadeia *i* regenerada** (mesmo `chain_id`). Elas recebem os mesmos pedidos, **na mesma ordem (A ou B)**, e a comparação é feita no mesmo passo. O pareamento não depende de as duas cadeias compartilharem uma semente aleatória do agente. Se o par for só um rótulo, o Wilcoxon pareado continua com nível correto; o que se perde é poder. Se o pareamento capturar algo real (mesma ordem, mesma máquina, mesma janela de tempo), o teste ganha poder. Por isso o pareamento é mantido. Quando um passo falha numa das duas cadeias do par, o par sai da comparação daquele passo e dos seguintes. A coluna `pares` de `diferenca_pareada.csv` mostra quantos pares sobram em cada passo.

### 2.2 Família de testes da correção de Holm

Família declarada antes dos dados. Uma linha por teste, com α = 0,05 e Holm sobre todas:

| # | Hipótese | Teste |
|---|---|---|
| 1 | H1 | GLMM: inclinação do passo (regenerado) |
| 2 | H4 | GLMM: interação modo × passo |
| 3 | H4 | Log-rank do passo da 1ª regressão |
| 4 | H2 | Crescimento de `files_touched`: modo × passo |
| 5 | H2 | Crescimento de `dup_pct`: modo × passo |
| 6 | H5 | GLMM: pedido que tensiona (regressão) |
| 7 | H5 | Modelo misto: pedido que tensiona (violações novas) |
| 8 | H3 | Spearman variância entre cadeias × passo (incremental) |
| 9 a 18 | Extra | Wilcoxon pareado, passos 1 a 10 |

Os modelos de sensibilidade não entram na família: GEE, GLMM com covariáveis, log-rank com outros tratamentos da censura e crescimento de `arch_violations`. Eles servem para mostrar se a conclusão depende de uma escolha de método.

### 2.3 Covariáveis: `agent_ran_tests` e ordem dos pedidos

- **Ordem (A ou B).** O esquema congelado não tem uma coluna de ordem. Ela é deduzida do pedido do passo 1: P1 é a Ordem A e P2 é a Ordem B (`models.ordem_das_cadeias`). Ela entra como covariável no modelo de sensibilidade.
- **`agent_ran_tests`.** Fica **fora do modelo principal** porque é pós-tratamento: o próprio agente decide, durante o passo, se roda os testes. Ajustar por ela pode absorver parte do efeito do modo. Por isso ela entra só no modelo de sensibilidade `glmm_covariaveis.csv` (`y ~ modo × passo + agent_ran_tests + ordem`).
- **Como ler:** se o termo modo × passo muda pouco entre `glmm.csv` e `glmm_covariaveis.csv`, a conclusão de H1/H4 não depende dessas covariáveis.

### 2.4 Plano B e diagnóstico dos modelos

- Se o GLMM não for estimável, o **GEE binomial com correlação permutável** vira o modelo principal, o que fica registrado na coluna `modelo` de `glmm.csv`. Isso acontece, por exemplo, quando nenhum teste falha ou todos falham.
- As curvas de crescimento tentam primeiro intercepto e inclinação aleatórios. Em cada formulação, testam os otimizadores lbfgs, powell, nm e bfgs até um convergir. Se não houver convergência com inclinação, o modelo cai para só intercepto.
- `results/modelos/diagnostico.csv` traz, para cada modelo, cada verificação com o valor observado, se passou e o que fazer quando não passa. As verificações são:
  - eventos por modo (separação);
  - efeito de cadeia perto de zero (ajuste singular);
  - sobredispersão;
  - concordância entre GLMM e GEE;
  - convergência;
  - normalidade e assimetria dos resíduos.
- Para contagens com resíduos assimétricos, a diferença pareada não paramétrica (seção 5.6) é a conferência.

### 2.5 Censura

O tratamento principal censura a cadeia que termina por passo falho no último passo concluído. A sensibilidade (`log_rank_sensibilidade.csv`) repete o log-rank de dois outros jeitos: contando a falha como evento (pior caso) e excluindo essas cadeias.

## 3. Ressalvas de leitura

- Os efeitos são **associações deste experimento**: uma stack, um modelo (`claude-sonnet-5-5`) e uma versão do Claude Code. Não se generalizam a outros agentes ou sistemas.
- Todo valor-p vem acompanhado do tamanho de efeito: odds ratio no GLMM, coeficiente nos modelos mistos e delta de Cliff na comparação pareada.
- Os "IC 95%" do GLMM (Bayes variacional) são intervalos de credibilidade aproximados e tendem a ser estreitos. Os erros robustos do GEE são a conferência.
- Nenhum índice composto: cada métrica é lida na sua unidade.

## 4. Resumo da coleta

_A preencher com `results/descritiva/resumo_da_coleta.csv`._

| Modo | Cadeias | Passos executados | Passos ok | Novas tentativas | Censuradas por falha | Completas | Custo (USD) | Duração (h) |
|---|---|---|---|---|---|---|---|---|
| incremental | | | | | | | | |
| regenerado | | | | | | | | |

- Cadeias por ordem (A/B), por modo: _a preencher_
- Desvios de protocolo (`desvios.md`): _a preencher_
- Testes instáveis (`flaky` > 0): _a preencher_

---

## 5. Resultados

> Nesta seção só entram números e o que eles mostram. A interpretação fica na seção 6.

### 5.1 Descritiva por modo e passo

_Tabela resumida de `descritiva/por_passo.csv`: n e censura por passo, taxa de regressão, regressão acumulada, violações, arquivos e módulos tocados, duplicação._

Figuras: `figures/regressao_por_cadeia.png`, `figures/regressao_acumulada.png`, `figures/estrutura_por_passo.png`.

### 5.2 H5: cabe × tensiona (descritiva)

_`descritiva/por_tipo_de_pedido.csv` e `figures/cabe_tensiona.png`._

### 5.3 H1 e H4: GLMM da regressão

| Termo | Odds ratio | IC 95% | p | p (Holm) |
|---|---|---|---|---|
| passo (regenerado) | | | | |
| modo × passo | | | | |

- Modelo usado (GLMM ou plano B): _a preencher_
- GEE (sensibilidade): _a preencher_
- GLMM com `agent_ran_tests` e ordem: _a preencher_
- Diagnóstico (`modelos/diagnostico.csv`): _a preencher, citando cada verificação que falhou_

### 5.4 H2, H3 e H5: modelos mistos

| Desfecho | Termo | Coeficiente | IC 95% | p | p (Holm) | Efeitos aleatórios |
|---|---|---|---|---|---|---|
| files_touched | modo × passo | | | | | |
| dup_pct | modo × passo | | | | | |
| arch_violations | modo × passo | | | | (fora da família) | |

- H3: Spearman variância × passo por modo (`modelos/h3_tendencia.csv`): _a preencher_
- H5: efeito de pedido que tensiona (`modelos/h5_tipo_de_pedido.csv`): _a preencher_

### 5.5 Sobrevivência (H4)

_`sobrevivencia/kaplan_meier.csv`, `figures/kaplan_meier.png`._

| Tratamento da falha | χ² | p | Cadeias | Eventos |
|---|---|---|---|---|
| censura (principal) | | | | |
| evento | | | | |
| exclui | | | | |

### 5.6 Diferença incremental − regenerado por passo

_`diferenca-pareada/diferenca_pareada.csv`, `figures/diferenca_pareada.png`: pares, diferença mediana com IC 95%, Wilcoxon p, p de Holm e delta de Cliff com IC 95%, por passo._

### 5.7 Correção de Holm

_`testes_holm.csv` completo, com p e p de Holm lado a lado._

### 5.8 Codificação das decisões do Claude Code

_Kappa de Cohen entre os 2 avaliadores, por categoria e final, de `docs/s02/codificacao-decisoes.md` (#121). Uso descritivo._

### 5.9 Auditoria manual × métricas automáticas

_Verdadeiros e falsos positivos e negativos dos testes e do ArchUnit, de `docs/s02/auditoria-manual.md`, seção 5._

---

## 6. Interpretação

> Seção separada dos resultados. Cada afirmação aponta para a linha da seção 5 que a sustenta.

| Hipótese | Resposta (sim / não / inconclusivo) | Evidência | Incerteza |
|---|---|---|---|
| H1 | | | |
| H2 | | | |
| H3 | | | |
| H4 | | | |
| H5 | | | |

## 7. Ligação com as ameaças à validade

_Para cada ameaça de `docs/s02/ameacas-a-validade.md` que os dados confirmaram ou afastaram, citar o número que mostra isso. Por exemplo:_
- _1.1 poder: número final de cadeias × simulação de poder;_
- _1.3 poucos dados nos passos avançados: coluna `pares` e `cadeias_ok`;_
- _2.1 ordem: termo `ordem_b`;_
- _2.3 censura: sensibilidade do log-rank;_
- _3.3 auditoria: falsos negativos._

## 8. Revisão

| Papel | Membro | Revisou? |
|---|---|---|
| B | @DevMiguelDiniz | _pendente_ |
