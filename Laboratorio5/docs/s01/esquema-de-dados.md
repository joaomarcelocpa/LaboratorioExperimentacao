# Esquema de dados do CSV por passo (S01)

Base: PLANEJAMENTO.pdf, seção 3.5. Versão executável: `analysis/schema.py` (lista `COLUNAS` e função `validar`). **O esquema é congelado desde o piloto:** as 32 colunas abaixo, nesta ordem, com estes tipos. Mudar uma coluna depois do piloto é desvio de protocolo.

## Regras gerais

- **Uma linha por (cadeia, modo, passo).** Chave: `(chain_id, mode, step)`, sem repetição.
- **Passo 0 = semente.** Existe uma linha de passo 0 por cadeia e modo, com a linha-base do produto (medidas do estado inicial) e sem execução do agente (colunas de execução vazias, `run_ok = 1`, `retry = 0`, `status = ok`). No piloto, o passo 0 não conta como execução do Claude Code: as 24 execuções são os passos 1 a 4.
- **Dados brutos nunca são sobrescritos:** novas linhas são acrescentadas ao CSV, e cada passo grava a linha uma vez (seção 3.5 do planejamento).
- **Falha de passo:** erro de execução, tempo esgotado ou build quebrado ao final, depois da **nova tentativa** (`retry = 1`). A linha fica com `status = falha`, `build_ok = 0`, e as medidas do produto vazias; **a cadeia termina** (não há linhas de passos seguintes) e o dado é censurado na análise. Regressão de teste **não** é falha de passo: a cadeia continua.
- **Codificação:** UTF-8, separador vírgula, ponto decimal, cabeçalho na primeira linha, vazio = ausente (nunca `0` no lugar de "não medido"), tempos em ISO 8601 UTC.
- **Metadados da coleta** (versão do Claude Code, modelo, data, versões das ferramentas de medição) vão em `tool_version` e `model_id` por linha e em um `METADADOS.md` ao lado dos dados na S02. Essas duas colunas são constantes durante a coleta.

## Colunas

| # | Coluna | Tipo | Unidade | Regra de preenchimento | Vazia quando |
|---|---|---|---|---|---|
| 1 | `chain_id` | inteiro | índice | 1..K. O mesmo índice nos dois modos forma o par da análise pareada | nunca |
| 2 | `mode` | texto | categoria | `incremental` ou `regenerado` | nunca |
| 3 | `step` | inteiro | passo | 0 a 10 | nunca |
| 4 | `request_id` | texto | — | `P0` a `P10`. No regenerado, o último pedido incluído no prompt acumulado | nunca |
| 5 | `request_type` | texto | categoria | `semente` (passo 0), `cabe` ou `tensiona`, conforme a marcação do pedido | nunca |
| 6 | `timestamp` | texto | ISO 8601 UTC | Fim da execução do passo, ex.: `2026-11-20T14:03:11Z` | nunca |
| 7 | `tool_version` | texto | versão | Saída de `claude --version`. Constante na coleta | nunca |
| 8 | `model_id` | texto | id | Modelo fixado (`claude-sonnet-5-5`). Constante na coleta | nunca |
| 9 | `tokens_in` | inteiro | tokens | Soma dos tokens de entrada de todos os turnos, incluindo cache, do JSON de saída | passo 0 |
| 10 | `tokens_out` | inteiro | tokens | Soma dos tokens de saída | passo 0 |
| 11 | `cost_usd` | decimal | USD | Custo reportado pelo Claude Code | passo 0 |
| 12 | `duration_s` | decimal | segundos | Duração de parede da execução | passo 0 |
| 13 | `turns` | inteiro | contagem | Número de turnos do agente | passo 0 |
| 14 | `agent_ran_tests` | 0/1 | — | 1 se o transcript mostra o agente rodando testes por conta própria | passo 0 |
| 15 | `run_ok` | 0/1 | — | 1 se a execução (tentativa final) terminou sem erro nem tempo esgotado | nunca |
| 16 | `retry` | 0/1 | — | 1 se houve a nova tentativa (a primeira falhou). `run_ok = 0` exige `retry = 1` | nunca |
| 17 | `build_ok` | 0/1 | — | 1 se o build compila no fim do passo | — (preenchida; 0 na falha) |
| 18 | `boot_ok` | 0/1 | — | 1 se `docker compose` sobe e `/health` responde 200 | passo com falha |
| 19 | `reg_total` | inteiro | contagem | Testes de regressão executados (HTTP e interface) | passo com falha |
| 20 | `reg_failed` | inteiro | contagem | Testes de regressão que falham nas **duas** rodadas. ≤ `reg_total` | passo com falha |
| 21 | `acc_total` | inteiro | contagem | Testes de aceitação do pedido atual | passo com falha |
| 22 | `acc_failed` | inteiro | contagem | Testes de aceitação do pedido atual que falham nas duas rodadas. ≤ `acc_total` | passo com falha |
| 23 | `flaky` | inteiro | contagem | Testes (regressão + aceitação) com resultado diferente entre as duas rodadas | passo com falha |
| 24 | `arch_violations` | inteiro | contagem | Violações ArchUnit **no estado** do workspace (não é delta) | passo com falha |
| 25 | `cycles` | inteiro | contagem | Ciclos entre pacotes no grafo de dependências (jdeps) | passo com falha |
| 26 | `files_touched` | inteiro | contagem | Arquivos do diff do commit do passo, sem `target/` e sem `.md` | passo com falha |
| 27 | `modules_touched` | inteiro | contagem | Módulos distintos dos arquivos Java de `src/main/java` no diff. ≤ `files_touched` | passo com falha |
| 28 | `max_ccn` | inteiro | complexidade | Maior complexidade ciclomática de uma função (Lizard) | passo com falha |
| 29 | `dup_pct` | decimal | % | Percentual de linhas duplicadas (jscpd), de 0 a 100 | passo com falha |
| 30 | `loc` | inteiro | linhas | Linhas de código Java de `src/main` (Lizard `nloc`: sem testes, brancos nem comentários) | passo com falha |
| 31 | `doc_drift` | inteiro | contagem | Regras do `ARCHITECTURE.md` violadas + módulos do código que o documento não menciona | passo com falha |
| 32 | `status` | texto | categoria | `ok` ou `falha` (após a nova tentativa) | nunca |

As colunas 24 a 31 são produzidas por `metrics/` (ver `python -m metrics.coletar`), com os mesmos nomes. As colunas 9 a 14 vêm do transcript e do JSON do Claude Code; 15 a 23 vêm do harness.

## Validação automática

`analysis.schema.validar(df)` devolve a lista de problemas. Além de colunas e domínios, confere: `reg_failed ≤ reg_total`, `acc_failed ≤ acc_total`, `modules_touched ≤ files_touched`, `dup_pct` em [0, 100], contagens não negativas, ausência de linhas depois de uma falha, passos contíguos a partir de 0, passo 0 com `request_type = semente`, e que `tool_version` e `model_id` são constantes. O pipeline recusa um CSV inválido (`python -m analysis.run --entrada <csv>`).

## Ordem dos pedidos

A ordem dos pedidos (as 2 ordens equivalentes da S02) **não é uma coluna**: o esquema segue exatamente as colunas do planejamento. Fica registrada no protocolo da S02 por `chain_id` (por exemplo, índice ímpar = ordem A, par = ordem B) e pela sequência de `request_id` no modo incremental. Se o grupo preferir uma coluna `order`, a mudança deve ser feita **antes do piloto**, não depois.
