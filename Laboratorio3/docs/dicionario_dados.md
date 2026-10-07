# Dicionário de dados

> **Arquivo gerado.** Não edite à mão: rode `python -m metricas.dicionario`.
> A fonte é `metricas/schemas.py`.

Convenções de todo o estudo:

- Chave de todo CSV: `repo`, no formato `owner/nome`.
- Datas em ISO 8601 UTC.
- Durações em horas.
- Proporções em 0–1.
- Valor ausente é vazio no CSV (`NaN` ao ler com pandas) e significa que a
  métrica não pôde ser calculada para aquele repositório.

## `candidatos.csv`

**Dono:** A

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `estrelas` | int | contagem | search/repositories: stargazers_count |
| `faixa_estrelas` | str | intervalo | fatia de busca do config.yaml |

## `commits.csv`

**Dono:** B

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `release_tag` | str | nome | release que inclui o commit |
| `sha` | str | sha1 | compare: commits[].sha |
| `data_autor` | data | ISO 8601 UTC | compare: commits[].commit.author.date |
| `autor_login` | str | login | compare: commits[].author.login |
| `eh_bot` | bool | sim/não | login termina em [bot] ou está em config.bots |
| `mensagem` | str | texto | compare: commits[].commit.message |

## `custo_api.csv`

**Dono:** C

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `endpoint` | str | caminho | endpoint chamado |
| `chamadas` | int | contagem | chamadas que saíram da máquina |
| `do_cache` | int | contagem | respostas servidas pelo cache |

## `deployments.csv`

**Dono:** B

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `id` | int | identificador | deployments: id |
| `environment` | str | nome | deployments: environment |
| `criado_em` | data | ISO 8601 UTC | deployments: created_at |
| `sha` | str | sha1 | deployments: sha |
| `estado_final` | str | success\|failure\|... | deployments/{id}/statuses: state |

## `descartes.csv`

**Dono:** A

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `etapa` | str | nome | etapa do funil em que caiu |
| `motivo` | str | texto | razão do descarte |

## `episodios.csv`

**Dono:** C

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `workflow_id` | int | identificador | runs.workflow_id |
| `inicio` | data | ISO 8601 UTC | run_started_at da primeira falha |
| `fim` | data | ISO 8601 UTC | updated_at do próximo sucesso |
| `horas` | float | horas | fim - inicio |
| `censurado` | bool | sim/não | episódio sem sucesso até o fim da janela |
| `so_flaky` | bool | sim/não | falha e sucesso no mesmo head_sha |

## `funil.csv`

**Dono:** A

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `etapa` | str | nome | etapa do filtro de seleção |
| `entraram` | int | contagem | repositórios na entrada da etapa |
| `sairam` | int | contagem | repositórios descartados na etapa |
| `motivo` | str | texto | razão do descarte |

## `issues_bug.csv`

**Dono:** A

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `numero` | int | contagem | issues: number |
| `criada_em` | data | ISO 8601 UTC | issues: created_at |
| `labels` | str | lista separada por ; | issues: labels[].name |
| `titulo` | str | texto | issues: title |
| `cita_tag` | bool | sim/não | título ou corpo cita a tag de uma release |

## `metricas.csv`

**Dono:** Todos

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `freq_release` | float | releases/semana | RQ01: releases na janela ÷ 52,1 |
| `freq_release_pre` | float | releases/semana | RQ01 variante: releases + pré-releases ÷ 52,1 |
| `freq_tag` | float | tags/semana | RQ01 variante: tags ÷ 52,1 |
| `freq_deploy` | float | deploys/semana | RQ01 variante: deployments em produção ÷ 52,1 |
| `lt_release_h` | float | horas | RQ02a: mediana de (data da release - commit mais antigo) |
| `lt_commit_h` | float | horas | RQ02b: mediana por commit |
| `lt_commit_sem_bots_h` | float | horas | RQ02b excluindo commits de bot |
| `pct_commits_bot` | float | proporção 0-1 | commits de bot ÷ total de commits |
| `cfr_a` | float | proporção 0-1 | RQ03a: falhas ÷ (falhas + sucessos) na conclusion listada |
| `cfr_a_bruto` | float | proporção 0-1 | RQ03a incluindo tentativas anteriores |
| `cfr_a_sem_flaky` | float | proporção 0-1 | RQ03a: o CFR bruto menos as falhas flaky (sucesso posterior no mesmo workflow e head_sha) |
| `pct_falhas_flaky` | float | proporção 0-1 | falhas flaky ÷ total de falhas do CFR bruto; NaN se não houver falhas |
| `cfr_b` | float | proporção 0-1 | RQ03b: releases seguidas de corretiva em 7 dias ÷ releases avaliadas |
| `cfr_c` | float | proporção 0-1 | RQ03c: releases seguidas de issue de bug em n_dias_issue |
| `recuperacao_h` | float | horas | RQ04: mediana dos episódios de falha |
| `recuperacao_sem_flaky_h` | float | horas | RQ04 ignorando episódios só de flaky |
| `pct_censurados` | float | proporção 0-1 | episódios censurados ÷ total de episódios |
| `recuperacao_releases_h` | float | horas | horas entre a release que falhou e a corretiva |
| `rework_rate` | float | proporção 0-1 | RQ08a: releases corretivas ÷ releases avaliadas, sem limite de dias |
| `rework_rate_7d` | float | proporção 0-1 | RQ08a variante: corretiva em até 7 dias da anterior |
| `nota_freq` | int | 1-4 | tabela de cortes DORA sobre freq_release |
| `nota_lead_time` | int | 1-4 | tabela de cortes DORA sobre lt_release_h |
| `nota_cfr` | int | 1-4 | tabela de cortes DORA sobre cfr_a |
| `nota_recuperacao` | int | 1-4 | tabela de cortes DORA sobre recuperacao_h |
| `classe_dora` | str | Elite\|High\|Medium\|Low | mediana das quatro notas, arredondada para baixo |
| `classe_dora_nota` | int | 1-4 | a mesma mediana, como inteiro, para o kappa ponderado da RQ07 |

## `metricas_mensais.csv`

**Dono:** C

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `mes` | mes | AAAA-MM | mês da janela |
| `cfr_a` | float | proporção 0-1 | RQ08b: CFR de CI do mês; NaN se runs_validos < 5 |
| `recuperacao_h` | float | horas | RQ08b: mediana do tempo de recuperação no mês; NaN se runs_validos < 5 |
| `runs_validos` | int | contagem | runs de sucesso + falha no mês |

## `releases.csv`

**Dono:** B

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `tag` | str | nome | releases: tag_name |
| `publicada_em` | data | ISO 8601 UTC | releases: published_at |
| `prerelease` | bool | sim/não | releases: prerelease |
| `na_janela` | bool | sim/não | publicada_em dentro de janela |
| `body` | str | texto | releases: body (release notes) |

## `releases_ignoradas.csv`

**Dono:** B

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `tag` | str | nome | releases: tag_name |
| `motivo` | str | texto | 404 no compare, sem release anterior etc. |

## `repos.csv`

**Dono:** A

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `estrelas` | int | contagem | repos/{owner}/{repo}: stargazers_count |
| `linguagem` | str | nome | repos/{owner}/{repo}: language |
| `criado_em` | data | ISO 8601 UTC | repos/{owner}/{repo}: created_at |
| `idade_anos` | float | anos | janela.fim - criado_em |
| `default_branch` | str | nome | repos/{owner}/{repo}: default_branch |
| `contribuidores` | int | contagem | contributors?per_page=1&anon=true: última página do Link |
| `owner_tipo` | str | User\|Organization | repos/{owner}/{repo}: owner.type |
| `org_verificada` | bool | sim/não | orgs/{org}: is_verified |
| `automacao_release` | bool | sim/não | presença de .releaserc*, release-please-config.json, .changeset/ ou .goreleaser.y*ml |
| `ferramenta_release` | str | nome | semantic-release\|release-please\|changesets\|goreleaser\|nenhuma |
| `pct_conventional` | float | proporção 0-1 | % de commits.mensagem que casam com o regex de Conventional Commits |

## `run_attempts.csv`

**Dono:** C

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `run_id` | int | identificador | actions/runs: id |
| `tentativa` | int | contagem | actions/runs/{id}/attempts/{n}: run_attempt |
| `conclusion` | str | success\|failure\|... | attempts/{n}: conclusion |
| `inicio` | data | ISO 8601 UTC | attempts/{n}: run_started_at |
| `fim` | data | ISO 8601 UTC | attempts/{n}: updated_at |

## `runs.csv`

**Dono:** C

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `run_id` | int | identificador | actions/runs: id |
| `workflow_id` | int | identificador | actions/runs: workflow_id |
| `workflow_nome` | str | nome | actions/runs: name |
| `event` | str | push\|schedule\|... | actions/runs: event |
| `head_sha` | str | sha1 | actions/runs: head_sha |
| `run_attempt` | int | contagem | actions/runs: run_attempt |
| `conclusion` | str | success\|failure\|... | actions/runs: conclusion |
| `classe` | str | sucesso\|falha\|ignorado | tabela de conclusion da seção 3 do enunciado |
| `inicio` | data | ISO 8601 UTC | actions/runs: run_started_at |
| `fim` | data | ISO 8601 UTC | actions/runs: updated_at |
| `criado_em` | data | ISO 8601 UTC | actions/runs: created_at |

## `tags.csv`

**Dono:** B

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `repo` | str | owner/nome | chave do estudo |
| `tag` | str | nome | tags: name |
| `sha` | str | sha1 | tags: commit.sha |
| `data_commit` | data | ISO 8601 UTC | commits/{sha}: commit.author.date |
