# Resumo da Sprint 1 — Laboratório 3 (métricas DORA)

Documento de apoio: o que a sprint exigia, o que foi feito, o que travou, o que foi otimizado e quais dados existem hoje. Os números são da rodada de 100 repositórios de 08/10/2026.

## 1. O que a Sprint 1 exigia

**Entrega (ESPECIFICACAO.md):** pipeline de coleta funcionando para **100 repositórios**, com testes e CI, mais a **introdução do artigo com uma hipótese por pergunta de pesquisa (RQ)**, escrita antes de ver os dados.

Para isso o pipeline precisa, em ordem:

| # | Etapa | Regra do enunciado |
|---|---|---|
| 1 | Listar candidatos | Busca por faixas de estrelas; a API devolve no máximo 1.000 resultados por consulta, então a faixa é dividida quando enche |
| 2 | Filtrar e registrar o funil | Usa GitHub Actions; ≥ 5 releases e ≥ 50 execuções de CI válidas na janela; sem forks e sem arquivados; sorteio reproduzível (seed) |
| 3 | Coletar releases e tags | Release = publicada, sem rascunho; pré-release fica só como variante; tag com a data do commit |
| 4 | Coletar commits entre releases | Base do lead time e da heurística de release corretiva |
| 5 | Coletar execuções de CI | Só o branch principal, só `push`, classificadas em sucesso / falha / ignorar; tentativas anteriores (instabilidade) |
| 6 | Coletar deployments e metadados | Deployments de produção; estrelas, linguagem, idade, contribuidores, tipo de dono, automação de release, % de Conventional Commits |
| 7 | Coletar issues de bug | Base do CFR (c) |
| 8 | Calcular as métricas | Frequência, lead time (a/b), CFR (a/b/c), tempo de recuperação, rework rate (bônus) |
| 9 | Classificar | Nota 1–4 por métrica; classe final = mediana, arredondada para baixo |
| 10 | Garantias | Cache e retomada, rate limit, testes, CI, Docker, README, dicionário de dados, código sem biblioteca pronta de API |

Janela de observação fixada: **2025-10-01 a 2026-09-30**.

## 2. O que cada um fez

Três partes, cada uma com a sua pergunta: **quais repositórios entram e o que eles são** (João Marcelo), **o que eles lançaram e quanto demoraram** (Bernardo) e **como o CI deles se comportou, mais toda a infraestrutura** (Miguel). Para cada parte: o que o código faz, o que baixa da API, o que grava e como calcula.

### 2.1 João Marcelo — quais repositórios entram, o que eles são e a classificação final

**Seleção dos candidatos** (`coleta/selecao.py`)
- Pergunta à busca do GitHub: "repositórios com 1.000 a 2.000 estrelas", depois "2.000 a 5.000", "5.000 a 10.000", "10.000 a 50.000" e "mais de 50.000". As faixas ficam no `config.yaml`.
- A busca devolve no máximo 1.000 resultados. Se uma faixa tem 1.000 ou mais, o código a divide ao meio e busca de novo, até cada pedaço caber. Nada se perde.
- Remove repetidos (as faixas se encostam nas pontas), forks e repositórios arquivados.
- Grava `candidatos.csv`: repositório, estrelas e faixa. Rodada de 100: 37.353 candidatos.

**Filtros** (`coleta/filtros.py`): três testes, do mais barato ao mais caro, para não gastar chamadas à toa:
1. **Usa GitHub Actions?** Se não tem nenhum workflow, não há execuções de CI para medir.
2. **Tem pelo menos 5 releases na janela?** Conta só releases publicadas, sem rascunho e sem pré-release (definição de deploy do enunciado).
3. **Tem pelo menos 50 execuções de CI válidas na janela?** Conta execuções do branch principal, disparadas por `push`, com resultado sucesso ou falha.

Quem passa nos três é aprovado. O código examina os candidatos em **ordem sorteada pela seed** e para ao chegar em 100 aprovados (a mesma seed reproduz a mesma amostra). Esse "para ao chegar" foi implementado em paralelo por João Marcelo e por Miguel (a versão do Miguel é a que ficou no código); o corte prévio por `pushed_at` (descarta quem não teve push desde o início da janela) é do Miguel.

**Funil e descartes**
- `funil.csv`: para cada etapa, quantos entraram e quantos saíram, e o motivo. O código confere que a conta fecha.
- `descartes.csv`: cada repositório excluído, com etapa e motivo.

**Metadados e fatores** (`coleta/metadados.py`, `coleta/fatores.py`) → `repos.csv`, uma linha por repositório:
- estrelas, linguagem, data de criação, idade em anos até o fim da janela e branch principal;
- **número de contribuidores**, sem baixar a lista: pede 1 contribuidor por página e lê o número da última página;
- tipo de dono (pessoa ou organização) e se a organização é verificada;
- **automação de release:** procura na raiz arquivos de ferramentas como `.releaserc`, `release-please-config.json`, `.changeset` e `.goreleaser.yml`, e menções a elas nos arquivos de workflow. Grava se há automação e qual ferramenta;
- **% de Conventional Commits:** parte dos commits cuja primeira linha segue o padrão `feat:`, `fix(escopo):`, etc.

Esses campos são os "fatores" da RQ 06, para comparar quem se sai melhor.

**Issues de bug** (`coleta/issues.py`) → `issues_bug.csv`
- Baixa as issues com os rótulos `bug`, `regression` ou `type: bug`, atualizadas desde o início da janela, sem pull requests. Uma issue com dois rótulos entra uma vez.
- Para cada uma, anota se o título ou o corpo **cita a tag de alguma release** (`cita_tag`). `v1.2.3` não casa com `v1.2.30`.

**CFR por issues** (`cfr_issues` em `metricas/cfr.py`)
- Uma release "falhou" se alguém abriu uma issue de bug entre o dia da publicação e 7 dias depois. A taxa é releases que falharam ÷ releases avaliadas.
- Releases dos últimos 7 dias da janela ficam de fora (não deu tempo de falhar). Repositório sem nenhuma issue de bug dá "vazio", e não 0%.

**Classificação DORA** (`metricas/classificacao.py`)
- Transforma cada métrica em nota de 1 a 4 pelos cortes do enunciado (por exemplo, lead time menor que 1 dia vale 4). A classe do repositório é a **mediana das quatro notas, arredondada para baixo**: (4, 3, 3, 1) dá High.

**Hipóteses** das RQ 01, 06 e 07, em `docs/hipoteses.md`.

### 2.2 Bernardo — releases, commits, tags e as métricas de entrega

**Coleta** (`coleta/releases.py`, `commits.py`, `deployments.py`)
- **Releases:** baixa todas, ignora rascunhos e marca quais são pré-release. Marca também `na_janela` (publicada dentro da janela) e guarda **a release imediatamente anterior à janela**, que serve de ponto de partida para comparar. Grava `releases.csv`.
- **Tags:** baixa a lista de tags de cada repositório, com a data do commit de cada uma. Grava `tags.csv`.
- **Commits entre releases:** para cada release da janela, pede ao GitHub a comparação com a release anterior e guarda cada commit: código, data do autor, login, mensagem e se é de **bot** (login termina em `[bot]` ou está na lista do config). Grava `commits.csv`. As releases sem anterior, ou em que a comparação deu 404, vão para `releases_ignoradas.csv`.
- **Deployments:** para os ambientes `production`, `prod` e `live`, guarda cada deployment e o estado final (sucesso, falha...). Grava `deployments.csv`.

**Métricas** (`metricas/frequencia.py`, `lead_time.py`, `corretiva.py`)
- **Frequência:** releases publicadas na janela ÷ semanas da janela (≈ 52,2). Existem as variantes por pré-release, por tag e por deployment.
- **Lead time (a), por release:** data da release − data do commit mais antigo incluído nela. O valor do repositório é a mediana das suas releases.
- **Lead time (b), por commit:** o mesmo para cada commit; o valor é a mediana de todos. Existe também a versão sem commits de bots e a % de commits de bots.
- **Release corretiva (heurística v0):** uma release é corretiva se **só o número de patch mudou** (2.3.0 → 2.3.1) **ou** se algum commit entre as duas tem `fix`, `hotfix` ou `revert` na mensagem.
- **CFR (b):** uma release falhou se foi seguida, em até 7 dias, por uma corretiva. Taxa = falhas ÷ avaliadas (últimos 7 dias da janela de fora).
- **Recuperação por release:** horas entre uma release que falhou e a corretiva que a seguiu.
- **Rework rate (bônus):** proporção de releases corretivas, sem limite de dias, e uma versão limitada a 7 dias.

**Hipóteses** das RQ 02, 03b e 08a.

### 2.3 Miguel — execuções de CI, recuperação e toda a infraestrutura

**A porta única para a API** (`coleta/http.py`, `coleta/cache.py`): toda chamada ao GitHub passa por aqui.
- **Cache em arquivo** (`data/raw/cache.sqlite`): cada resposta é guardada, inclusive as de "não encontrado". Rodar de novo não repete chamadas, e interromper no meio não perde nada.
- **Limite da API:** acompanha as chamadas restantes e dorme até a renovação quando sobram poucas; respeita o aviso de espera do GitHub.
- **Repetição em erro:** se o GitHub falha (erro 5xx), tenta de novo esperando 1, 2, 4, 8 e 16 segundos.
- **Custo:** conta quantas chamadas cada endpoint fez e quantas vieram do cache (`custo_api.csv`).
- Segue a paginação e trata a busca (30 por minuto) e as demais chamadas (5.000 por hora) como limites separados.

**Coleta das execuções de CI** (`coleta/runs.py`) → `runs.csv`
- Baixa as execuções de CI do branch principal, só as disparadas por `push`, dentro da janela.
- Cada resultado vira **sucesso, falha ou ignorado** pela tabela do enunciado (`success` é sucesso; `failure`, `timed_out` e `startup_failure` são falha; cancelado e pulado são ignorados).
- A API só devolve 1.000 resultados por consulta. O código pede mês a mês e, se um mês enche, **divide ao meio e repete**. Intervalos que não couberam nem assim vão para `fatias_saturadas.csv`.
- **Tentativas anteriores** (`run_attempts.csv`): quando uma execução foi rodada de novo, a listagem mostra só a última tentativa. O código busca as anteriores (até 5 por execução), para enxergar falhas que depois passaram.

**Medidas de CI** (`metricas/execucoes.py`, `cfr.py`, `recuperacao.py`, `mensais.py`)
- **Linha do tempo única:** junta execuções e tentativas anteriores, em ordem de data.
- **Instabilidade (flaky):** uma falha é "flaky" se, no mesmo workflow e no mesmo commit, houve um sucesso depois. O código passou sem mudar nada, então não era defeito.
- **CFR (a), três versões:** falhas ÷ (falhas + sucessos). *Oficial:* só as execuções da listagem. *Bruto:* inclui as tentativas anteriores. *Sem flaky:* o bruto sem as falhas instáveis. Também a % de falhas que eram instáveis.
- **Episódios de falha e recuperação** → `episodios.csv`:
  - em cada workflow, um episódio **começa na primeira falha depois de um sucesso** e **termina no próximo sucesso**;
  - o tempo de recuperação é a duração em horas, e o valor do repositório é a mediana;
  - episódio que não termina antes do fim dos dados é **censurado**: fica marcado e é contado (`pct_censurados`), mas fora da mediana, porque não tem duração conhecida;
  - também calcula a recuperação sem os episódios só de instabilidade.
- **Série mensal** → `metricas_mensais.csv`: CFR e recuperação por mês e por repositório (RQ 08b). Mês com menos de 5 execuções válidas fica vazio.

**Pipeline e entregas do projeto**
- **Pipeline único** (`pipeline/executar.py`): um comando faz seleção, filtros, coleta, metadados, runs, issues, métricas e CSVs. O `--limite N` define o tamanho da amostra.
- **Segurança da rodada:** grava os CSVs a cada repositório completo; um repositório que falha é anotado e isolado, sem derrubar os outros; um erro de token (401) interrompe tudo.
- **Estimativa de custo** (`pipeline/estimativa.py`): projeta chamadas e horas para 300 repositórios a partir de uma rodada menor.
- **Adaptador de sessão** (`coleta/sessao.py`): faz os coletores do Bernardo passarem pelo cache e pelo controle de limite sem reescrevê-los.
- **Leitura do token** (`pipeline/ambiente.py`), validação do `config.yaml` (`pipeline/config.py`), `Dockerfile`, `Makefile`, README e o CI do GitHub (testes e build do Docker).

### 2.4 Trabalho em conjunto nesta sprint (otimizações e correções)

| O que | Para que serve |
|---|---|
| Tags e deployments via GraphQL (`coleta/tags.py`, `coleta/deployments_graphql.py`) | Traz 100 por chamada em vez de 1 por item. Detalhes na seção 4 |
| Visão só de releases estáveis (`metricas/estaveis.py`) | As métricas principais deixam de contar pré-releases, e os commits de uma pré-release vão para a próxima release estável |
| Frequência principal sem pré-releases (`pipeline/montagem.py`) | Cumpre a definição de deploy do enunciado |
| `pipeline/montagem.py` | Junta tudo na linha de cada repositório de `metricas.csv` e calcula notas e classe |

### 2.5 Decisões de definição (seguem o enunciado)

- Deploy principal = release **sem** pré-release. Pré-releases só entram em `freq_release_pre`. O filtro de 5 releases, a frequência, o lead time, o CFR (b), o `cfr_c` e o rework usam só releases estáveis.
- `cfr_c` usa o modo `janela` (qualquer issue de bug nos 7 dias após a release). O modo `citacao` (a issue precisa citar a tag) existe no código, mas não está ligado.
- Classe DORA: tabela de cortes do enunciado.

Qualidade: **683 testes**, **96% de cobertura**, CI do GitHub passando.

Como rodar: `python -m pipeline --config config.yaml --limite 100` (precisa de `GITHUB_TOKEN` no `.env`).

## 3. Gargalos encontrados

Medidos com `custo_api.csv` (chamadas à API por endpoint). Limite da API: **5.000 chamadas por hora**; busca: 30 por minuto.

| Gargalo | Medido | Efeito |
|---|---|---|
| **Listar candidatos** | 788 buscas, ~41 min | Custo fixo, não cresce com a amostra |
| **Filtro examinando todos os candidatos** | 37 mil candidatos × ~3 chamadas | Centenas de milhares de chamadas, dias de cota |
| **Leitura de tags** (uma chamada por tag) | 52% das chamadas na rodada do Miguel; 80–93% nos 5 repositórios que medi | `ruff`: 446 chamadas e 182 s só nisso |
| **Status de deployments** (uma chamada por deployment) | 446 chamadas num único repositório (`mockoon`), 36% da coleta de 10 repositórios | |
| **Coletores sem cache** | Rodar de novo repetia tudo | Corrigido com o adaptador de sessão |
| **Poucos repositórios gigantes** | 4 repositórios = 59% dos runs; `openvino` gerou 1.068 tentativas | Puxam o tempo da rodada de 100 para cima |

Gargalos que **continuam**, sem ganho fácil: `compare` entre releases (4.340 chamadas, 30%), tentativas de runs (2.694, 19%) e runs de CI (~3.000, 21%).

## 4. Otimizações feitas

| Otimização | Antes | Depois | Quem |
|---|---|---|---|
| **Filtro preguiçoso:** candidatos embaralhados pela seed, examinados um a um, para ao completar o alvo | todos os candidatos | **483 examinados** para 100 aprovados | Miguel e João |
| **Pré-filtro por `pushed_at`:** descarta quem não teve push desde o início da janela | 60.063 candidatos | 37.353 (22.710 cortados, sem chamada à API) | Miguel |
| **Cache + adaptador de sessão:** coletores antigos passam pelo cache e pelo rate limit; `per_page=100` em releases e tags | repetia chamadas | repetição custa quase zero | Miguel |
| **Tags via GraphQL:** 100 tags por chamada, com a data do commit | `ruff`: 446 chamadas, 182 s; `pytest`: 232 chamadas, 96 s | `ruff`: 5 chamadas, 2,9 s; `pytest`: 3 chamadas, 1,6 s. Resultado **idêntico** ao REST nos 5 repositórios comparados | João |
| **Deployments via GraphQL:** estado final junto da listagem | `mockoon`: 446 chamadas | 5 chamadas, 3,3 s. Resultado **idêntico** (446 = 446) | João |
| **Reserva REST:** se o GraphQL não acha o repositório (renomeado), cai no REST | — | sem perda de dados | João |

Efeito somado (estimativa, não medido): sem as otimizações de tags e deployments, a rodada de 100 teria passado de ~6 horas só de cota.

## 5. Tempos medidos

| Rodada | Tempo | Chamadas à API |
|---|---|---|
| 10 repositórios | 55 min (43 min de seleção, 12,6 min de coleta) | 2.195 |
| Reexecução dos 10 (tudo em cache) | 19 s | 9 |
| **100 repositórios** | **3h33** (9 min de seleção, ~3h24 de coleta) | 14.258 novas + 3.225 do cache |

Por repositório novo: ~146 chamadas e ~137 s (média, com cauda longa).

**Projeção para 300 (estimativa, extrapolação linear):** ~29.000 chamadas e ~8 h para os 200 repositórios novos. O cache evita refazer os 100 primeiros.

## 6. Dados encontrados e armazenados

Pasta `data/processed/`, no git. Resultado da rodada de 100: **99 repositórios coletados**. O `google-cloud-node` falhou (monorepo com tags por pacote; o `compare` deu erro 422) e ficou fora de todos os arquivos.

| Arquivo | Linhas | O que é |
|---|---|---|
| `candidatos.csv` | 37.353 | candidatos depois dos cortes |
| `funil.csv` | 8 etapas | como chegamos aos 100 |
| `descartes.csv` | — | cada exclusão, com etapa e motivo |
| `repos.csv` | 99 | metadados e fatores por repositório |
| `releases.csv` | 5.461 | releases (com flag de janela e pré-release) |
| `tags.csv` | 42.977 | tags com a data do commit |
| `commits.csv` | 91.421 | commits entre releases (**54 MB**) |
| `runs.csv` | 193.700 | execuções de CI (35 MB) |
| `run_attempts.csv` | 2.748 | tentativas anteriores (instabilidade) |
| `deployments.csv` | 4.918 | deployments de produção (10 repositórios) |
| `issues_bug.csv` | 4.801 | issues de bug (71 repositórios) |
| `episodios.csv` | 4.624 | episódios de falha e recuperação |
| **`metricas.csv`** | **99** | **as métricas e a classe DORA por repositório** |
| `metricas_mensais.csv` | 987 | série mensal (RQ 08b) |
| `custo_api.csv`, `custo_selecao.csv` | — | chamadas por endpoint |
| `fatias_saturadas.csv` | 31 | intervalos de runs que passaram do teto da API |

Os 14 CSVs principais passam na validação do contrato. O cache bruto (`data/raw/cache.sqlite`, **4,9 GB**) fica fora do git. **Não apagar:** é ele que faz as próximas rodadas custarem só o que é novo.

### Funil da rodada de 100

| Etapa | Entraram | Saíram |
|---|---|---|
| Duplicata | 65.450 | 26 |
| Fork | 65.424 | 0 |
| Arquivado | 65.424 | 5.361 |
| Sem push na janela | 60.063 | 22.710 |
| Não examinados (amostra fechou) | 37.353 | 36.870 |
| Não usa Actions | 483 | 96 |
| Menos de 5 releases | 387 | 253 |
| Menos de 50 runs válidos | 134 | 34 |
| **Aprovados** | — | **100** |

### Resultado das métricas (99 repositórios)

| Métrica | Mediana |
|---|---|
| Releases por semana (`freq_release`) | 0,40 |
| Lead time por release (`lt_release_h`) | 137 h |
| CFR de CI (`cfr_a`) | 4,8% |
| CFR por release corretiva (`cfr_b`) | 43% |
| CFR por issues (`cfr_c`) | 33% |
| Tempo de recuperação (`recuperacao_h`) | 3,0 h |

Classes DORA: **12 Elite, 42 High, 38 Medium, 7 Low**.

## 7. Limitações dos dados

1. **`cfr_b` e `rework_rate` provavelmente inflados.** A mediana do `cfr_b` é 43% e, em 50 dos 99 repositórios, o `rework_rate` vale 1,0. A heurística atual marca uma release como corretiva se algum commit tiver `fix`, `hotfix` ou `revert` na mensagem, o que quase sempre ocorre. A validação manual da Sprint 2 mede isso.
2. **`cfr_c` ausente em 28 repositórios**, porque não têm issues com os labels `bug`, `regression` ou `type: bug`.
3. **31 fatias de runs saturadas** (24 no `pytorch`, 5 no `openvino`, 1 no `decidim`, 1 no `summarize`): parte dos runs desses intervalos ficou de fora. É ameaça à validade e precisa entrar no artigo.
4. **Amostra de 99, não 100**, por causa do monorepo. Falta uma regra de reposição para a Sprint 2.
5. **Falta o "tipo do projeto"** (biblioteca, aplicação, CLI), que é rotulado à mão na Sprint 2.
6. **Monorepos com tags por pacote** distorcem a cadeia de releases (lead time e CFR).

## 8. O que falta para fechar a Sprint 1

- Hipóteses das RQ 03a, 04, 05 e 08b (parte do Miguel) em `docs/hipoteses.md`.
- README final (funil, tempo, custo, limitações) e conferência do `funil.csv`.
- Fechar as issues #38, #39, #43, #44 e #45 no GitHub Projects.

## 9. Pontos a decidir antes da Sprint 2 (300 repositórios)

- **Tamanho do `commits.csv`:** deve passar de 100 MB e o GitHub vai recusar o push. Opções: Git LFS, versionar compactado (`.csv.gz`) ou commitar só nos marcos.
- **Heurística de release corretiva:** refinar com a validação manual (60 repositórios, kappa de Fleiss, precisão e recall).
- **Monorepos:** excluir, tratar por pacote ou registrar como ameaça.
- **Labels de bug:** ampliar a lista para reduzir os 28 repositórios sem `cfr_c`.
- **`cfr_c`:** manter `janela` ou passar para `citacao`.
- **Tempo da coleta:** ~8 h para os 200 novos; dividir entre os três tokens reduz para ~2,7 h cada.
