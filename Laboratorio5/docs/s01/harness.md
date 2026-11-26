# Harness de execução do piloto e da coleta

Issue #105 (papel B). Executa o Claude Code de forma não interativa, passo a passo, e grava uma linha por passo no CSV com o esquema congelado (`docs/s01/esquema-de-dados.md`, 32 colunas). O mesmo harness serve ao piloto (3 cadeias × 2 modos × P1 a P4 = 24 execuções) e à coleta completa (P1 a P10).

> **Estado:** o código e os testes unitários existem e passam (40 testes, com Claude Code falso). **Nenhuma execução real do agente foi feita**, nada foi rodado em container (o daemon do Docker estava desligado) e nenhum teste de aceitação de P1 a P4 foi exercitado por este harness. A seção "O que foi e o que não foi testado" detalha.

## Arquivos

| Arquivo | Papel |
|---|---|
| `harness/executar.py` | orquestra cadeias e piloto; protocolo por passo; linha do CSV |
| `harness/agente.py` | monta e roda o `claude -p`; lê tokens, custo, turnos; `agent_ran_tests` |
| `harness/pedidos.py` | texto do pedido que vai ao agente; prompt por modo |
| `harness/workspace.py` | cópia da semente, um commit por passo, restauração, isolamento |
| `harness/medicao.py` | build, `docker compose`, duas rodadas de testes, métricas (`metrics/coletar.py`) |
| `harness/csvpassos.py` | CSV só de acréscimo, com a chave `(chain_id, mode, step)` única |
| `harness/container/` | `Dockerfile` do agente, `construir-imagem.sh`, `verificar-imagem.sh`, `compose.override.yml` |
| `harness/check-env`, `ambiente.pins`, `plano_execucao.py` | verificação do ambiente e plano (issue #118) |
| `tests/test_harness.py`, `tests/harness_fake_claude.py` | testes com Claude Code falso |

## Como rodar

Pré-requisitos por máquina: `harness/check-env` conforme (versões em `harness/ambiente.pins`), Docker ativo, Python com `pandas`, `lizard`, e `jscpd` instalado. Veja `docs/s02/ambiente-de-coleta.md`.

```bash
cd Laboratorio5
# 1. imagem do agente na versão fixa do Claude Code, e conferência dela (em cada máquina)
harness/container/construir-imagem.sh
harness/container/verificar-imagem.sh

# 2. credencial só por variável de ambiente (nunca em arquivo montado)
export ANTHROPIC_API_KEY=...        # ou CLAUDE_CODE_OAUTH_TOKEN
export ANTHROPIC_MODEL=claude-sonnet-5-5 DISABLE_AUTOUPDATER=1

# 3. mostra o plano sem executar nada
python -m harness.executar piloto

# 4. executa (consome o plano do Claude Code: 24 execuções no piloto)
python -m harness.executar piloto --executar --maquina A
# ou uma cadeia só
python -m harness.executar cadeia --cadeia 1 --modo incremental --executar
```

- Sem `--executar` o comando só imprime o plano. O agente nunca roda sem esse flag.
- Antes de executar, o harness roda `harness/check-env` e aborta se o ambiente não estiver conforme. Os metadados vão para `results/pilot/ambiente-<máquina>-<data>.json`.
- Saídas: `results/pilot/passos.csv` (uma linha por passo), `results/pilot/execucoes.jsonl` (log bruto de cada tentativa), `results/pilot/transcripts/` (transcript de cada tentativa e seu `.stderr`).
- **Retomada:** rodar de novo ignora cadeias completas ou censuradas e continua uma cadeia parcial do próximo passo. Se o CSV tem linhas de uma cadeia mas o workspace sumiu ou não confere, o harness para: dado bruto não se sobrescreve, então o caso vira desvio e usa outro `chain_id`.
- As cadeias rodam em sequência na máquina, na porta 8080 do contrato. `BASE_URL` muda o endereço usado pelos testes.
- Os testes ocultos (`tests/regression` e `tests/acceptance`, esta última com uma classe `*Test` por pacote `p<n>`) rodam do host contra a aplicação do workspace.

## O que cada passo faz (seção 3.5)

1. **Workspace.** Cópia da semente (sem `target/` nem `.git`) em um repositório novo fora do laboratório (`HARNESS_WORK`, padrão `/tmp/lab05-harness`). Passo 0 = semente, medida sem executar o agente.
2. **Prompt.** Só o pedido (abaixo). No modo **incremental**, o passo *n* envia o pedido *n* sobre o workspace do passo anterior. No modo **regenerado**, o passo *n* parte de uma semente limpa e envia os pedidos 1 a *n* acumulados, em ordem, cada um sob um cabeçalho `PEDIDO k`.
3. **Agente.** Sessão nova, em container descartável, não interativa (flags abaixo).
4. **Um commit por passo.** Qualquer commit que o agente tenha feito é juntado, com tudo o que ele deixou, em um único commit sobre o estado do início do passo.
5. **Build.** `mvn -B -q -DskipTests package` no workspace. Falha de build conta como falha do passo.
6. **Regra de passo falho.** Erro do agente, tempo esgotado ou build quebrado: **uma** nova tentativa a partir do mesmo estado (workspace restaurado), com o mesmo prompt e sem feedback. Falhou de novo: a linha do passo sai com `status = falha`, `retry = 1`, `build_ok = 0` e medidas vazias, a cadeia termina (nenhum passo depois) e o dado é censurado.
7. **Medição (só se o passo deu certo).** `docker compose up` (projeto `lab05-harness`) e espera de `GET /health` 200 → `boot_ok`; regressão e aceitação do pedido atual **duas vezes** cada; `docker compose down -v`; métricas por `metrics/coletar.py` (colunas 24 a 31).
8. **Linha do CSV.** Escrita uma vez, no fim do passo, e validada no fim da execução por `analysis.schema.validar`.

Definições usadas nas colunas de teste: `reg_failed` e `acc_failed` são os testes que falham nas duas rodadas; `flaky` é o número de testes (regressão mais aceitação) com resultado diferente entre as rodadas; `reg_total` e `acc_total` contam os casos executados (ignorados não entram). Se a suíte de aceitação do pedido não tem nenhum teste, o harness para com erro em vez de gravar `acc_total = 0`. Falha de infraestrutura (Maven sem relatórios, por exemplo) também para sem gravar linha: um número errado no CSV é pior que um passo não registrado. Se a aplicação não sobe, os testes rodam mesmo assim contra o endereço morto e a regressão aparece como falha nas duas rodadas.

## O que vai ao agente

O texto enviado é o do arquivo do pedido entre os dois primeiros `---`, ou seja, as cinco seções do molde congelado (`[CONTEXTO]` a `[SAÍDA]`), mais a tabela "Mínimo observável" quando existe (cabeçalhos, endpoints e `data-testid` que os testes usam fazem parte do comportamento). **Não vão ao agente:** título, tipo (cabe/tensiona), ordem, rastreio critério↔teste, o "Contrato do stub (para escrita dos testes)" de P9 e as notas de rodapé. O tipo vem do cabeçalho do arquivo só para preencher `request_type` no CSV. `tests/test_harness.py` garante isso.

## Execução do agente

Flags conferidas em `claude --help` na versão 2.1.238 (a versão fixada em `ambiente.pins`, a mesma da máquina onde o harness foi escrito):

| Flag | Uso |
|---|---|
| `-p` | modo não interativo |
| `--model claude-sonnet-5-5` | modelo fixo |
| `--output-format stream-json --verbose` | um evento por linha, incluindo cada chamada de ferramenta e o evento final com custo, turnos e uso |
| `--permission-mode bypassPermissions` | sem pedir permissão; só aceitável dentro do container descartável |
| `--no-session-persistence` | sessão nova por passo, nada para retomar |
| `--setting-sources project` | não herda configuração do usuário (nem CLAUDE.md pessoal) |
| `--max-budget-usd` | opcional (`HARNESS_MAX_BUDGET_USD`) |

Variáveis: `DISABLE_AUTOUPDATER=1` e `ANTHROPIC_MODEL`.

- **`--max-turns` não existe no `--help` da 2.1.238.** O harness só o passa se o `--help` da versão em uso o listar (`HARNESS_MAX_TURNS`). Sem ele, o limite efetivo por passo é o tempo (`HARNESS_TIMEOUT_S`, padrão 1800 s, **provisório**).
- Os limites de turnos, de tempo e de orçamento por passo são decisão do grupo e estão em branco no protocolo congelado (seção 1).
- **Colunas do agente:** `tokens_in` soma entrada, criação de cache e leitura de cache; `tokens_out` é a saída; `cost_usd` e `turns` vêm do evento final; `duration_s` é o tempo de parede medido pelo harness. No CSV ficam os valores da **tentativa final**; o custo e o tempo da tentativa que falhou ficam só em `execucoes.jsonl` e precisam entrar na conta de orçamento.
- **`agent_ran_tests = 1`** se o transcript tem uma chamada Bash que roda o runner de testes: `mvn`/`mvnw` com `test`, `verify` ou `integration-test`, ou `package`/`install` sem `-DskipTests`, ou `pytest`, `npm test`, `-Dtest=`. É uma regra sobre o texto do comando; não prova que os testes rodaram até o fim.

## Isolamento e container

- Container por execução (`docker run --rm`), sem privilégios (`--cap-drop ALL`, `no-new-privileges`), usuário do host, 4 GB e 2 CPUs.
- **Só o workspace é montado.** `tests/acceptance` e `reference` nunca entram no container, e `workspace.verificar_isolamento` barra o passo se alguma pasta `acceptance` ou `reference` aparecer dentro do workspace ou se o workspace estiver dentro delas. A suíte oculta roda do host.
- Credenciais entram só por variável de ambiente (`ANTHROPIC_API_KEY` ou `CLAUDE_CODE_OAUTH_TOKEN`); nenhum arquivo do usuário é montado.
- `harness/container/verificar-imagem.sh` confere versão, atualização automática e ausência de pastas ocultas na imagem. Deve rodar nas três máquinas.
- P9: a cadeia que inclui P9 sobe com `compose.override.yml`, que injeta `NOTIFICACAO_URL` no serviço `app`. Se o agente renomear esse serviço, P9 precisa de tratamento manual. P1 a P4 não usam o override.

## Dados brutos

- `passos.csv` só recebe linhas novas; uma chave `(chain_id, mode, step)` repetida é recusada.
- Transcript e log nunca são sobrescritos (o transcript é aberto em modo exclusivo).
- Não apague nem edite `results/pilot/`. Um erro de execução vira desvio (`docs/s02/desvios.md`).

## Ética

- Os pedidos e os testes usam só dados sintéticos: nenhum dado pessoal nem real.
- Nenhum teste de carga contra sistema de terceiros. As cargas de P2 e P4 (50 mil tarefas, CSV de 20 mil linhas) vão só para a semente, no ambiente do grupo.
- As execuções do agente acontecem só na semente e no ambiente do grupo, dentro do container descartável. O agente não recebe credenciais além da própria.

## O que foi e o que não foi testado

**Testado (40 testes em `tests/test_harness.py`, com o Claude Code falso `tests/harness_fake_claude.py`, sem gastar o plano):**
- texto enviado ao agente: sem tipo, rastreio nem notas; mínimo observável presente; incremental envia um pedido, regenerado acumula em ordem;
- montagem do comando (flags, modelo, atualização automática, `--max-turns` só quando suportado) e do comando de container (um único volume, sem pastas ocultas);
- leitura de tokens (com cache), custo, turnos e transcript; `agent_ran_tests`; erro, ausência de resultado e tempo esgotado; transcript nunca sobrescrito;
- workspace: um commit por passo mesmo se o agente commitar, restauração para a nova tentativa, recusa de limpar fora da pasta de trabalho, barreira contra pastas ocultas;
- contagem de regressão e `flaky` pelas duas rodadas, relatório surefire, suíte de aceitação vazia recusada;
- cadeias completas nos dois modos, validadas por `analysis.schema.validar`; nova tentativa sem feedback; duas falhas e build quebrado terminando a cadeia; retomada sem repetir nem sobrescrever;
- build Maven e métricas estruturais reais sobre a semente (sem jscpd, ver abaixo).

**Não testado:**
- **Nenhuma execução real do Claude Code.** O formato do `stream-json` e os nomes dos campos do evento final (`usage`, `total_cost_usd`, `num_turns`, `is_error`, `subtype`) seguem o formato que o `claude -p` documenta, mas foram exercitados só contra o falso. Antes do piloto, rode **um** passo real e confira o transcript.
- **Todo o caminho de container:** `Dockerfile`, `construir-imagem.sh`, `verificar-imagem.sh`, `docker run` e `docker compose` (daemon desligado). Nada disso foi construído nem executado.
- **A medição real por testes:** `mvn test` das suítes de regressão e aceitação contra a aplicação do workspace via `Medidor`, e a espera de `/health`. Os testes usam um medidor falso com a mesma interface.
- **Os testes de aceitação de P1 a P4:** este harness roda as classes `*Test` do pacote `p<n>` em `tests/acceptance` (padrão por pacote, porque `P1*Test` casaria também `P10BancoTest`). Sem elas o harness para com erro.
- **jscpd e Lizard** não estão instalados na máquina de desenvolvimento (Lizard só no ambiente virtual dos testes), então `dup_pct` não foi medido de verdade (`check-env` também falha por isso).
- O piloto em si: nenhuma das 24 execuções foi feita, não há `results/pilot/` e o relatório do piloto (#109) continua sem dados.
