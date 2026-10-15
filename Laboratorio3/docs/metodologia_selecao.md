# Metodologia: seleção da amostra, funil e fatores

Parte do João (A) da seção de Metodologia (#67). Os números vêm de
`data/processed/funil.csv`, `repos.csv` e `metricas.csv` da rodada de 13 e 14
de outubro de 2026, e o tipo do projeto vem do consenso da amostra-ouro
(`data/conferencia/consenso_repositorios.csv`).

## 1. Fonte de dados e janela

Todos os dados vêm da API do GitHub (REST e GraphQL), coletados por script
próprio do grupo, sem bibliotecas prontas de acesso à API. A janela de
observação tem 12 meses, de **1º de outubro de 2025 a 30 de setembro de 2026**.
Só entram nas métricas releases publicadas e execuções de CI criadas dentro
dela.

## 2. Seleção da amostra

### 2.1 Candidatos

A população de interesse são repositórios públicos com pelo menos 1.000
estrelas. Como a busca do GitHub devolve no máximo 1.000 resultados por
consulta, os candidatos foram buscados em cinco faixas de estrelas
(1.000 a 2.000, 2.000 a 5.000, 5.000 a 10.000, 10.000 a 50.000 e acima de
50.000). Faixas que atingiam o teto foram partidas ao meio até cada pedaço
caber numa consulta. A busca devolveu **65.450** repositórios.

### 2.2 Limpeza dos candidatos

Antes de examinar qualquer repositório, foram removidos:

- **duplicatas** (as faixas se tocam nas pontas): 26;
- **forks**: 0;
- **arquivados**: 5.361;
- **sem push desde 1º/10/2025**: 22.710. A busca já traz a data do último
  push, e um repositório sem push na janela não pode ter 50 execuções de CI
  por push nela, então seria descartado de qualquer forma. Cortar aqui só
  economiza chamadas e não muda quem pode entrar.

Restaram **37.353** candidatos.

### 2.3 Critérios de inclusão

Os candidatos foram examinados nesta ordem, do critério mais barato ao mais
caro, e o primeiro que reprovava descartava o repositório:

1. **Usa GitHub Actions**: tem ao menos um workflow.
2. **Pelo menos 5 releases na janela**: publicadas, sem rascunhos e sem
   pré-releases.
3. **Pelo menos 50 execuções de CI válidas na janela**: no *default branch*,
   disparadas por `push`, com resultado de sucesso ou falha
   (`success`, `failure`, `timed_out`, `startup_failure`). Execuções canceladas,
   puladas ou em andamento não contam.

Os dois limites (5 e 50) são os fixados no enunciado.

### 2.4 Sorteio

Examinar os 37.353 candidatos custaria dias de cota da API (5.000 chamadas por
hora). Por isso os candidatos foram **embaralhados com seed fixa (42)** e
examinados nessa ordem, parando quando 300 foram aprovados. As primeiras 300
aprovações de uma ordem aleatória fixa formam uma amostra aleatória simples do
conjunto de repositórios aprovados, e a mesma seed reproduz a mesma amostra.

A amostra **não é estratificada** por faixa de estrelas, linguagem ou tipo. A
proporção de cada faixa na amostra reflete a proporção entre os repositórios
aprovados.

## 3. Funil de seleção

| Etapa | Entraram | Saíram | Motivo |
|---|---:|---:|---|
| Candidatos da busca | 65.450 | | |
| Duplicatas | 65.450 | 26 | já veio de outra faixa de estrelas |
| Forks | 65.424 | 0 | é um fork |
| Arquivados | 65.424 | 5.361 | está arquivado |
| Sem push na janela | 60.063 | 22.710 | sem push desde 1º/10/2025 |
| **Candidatos elegíveis** | **37.353** | | |
| Não examinados | 37.353 | 35.999 | a amostra fechou antes (ordem aleatória, seed 42) |
| Examinados | 1.354 | | |
| Usa GitHub Actions | 1.354 | 240 | não usa Actions |
| Mínimo de 5 releases | 1.114 | 711 | menos de 5 releases na janela |
| Mínimo de 50 execuções de CI | 403 | 103 | menos de 50 execuções válidas |
| **Aprovados** | **300** | | |

Entre os 1.354 examinados, 300 passaram nos três critérios (22%). Essa é a taxa
que vale para dizer quantos candidatos "passam nos filtros": não se pode usar o
total de 37.353, porque a maior parte nem foi examinada. A tabela completa e os
motivos de cada descarte estão em `funil.csv` e `descartes.csv`.

A coleta completa das métricas foi concluída para **299 dos 300** aprovados. A
análise usa esses 299.

## 4. Fatores usados para comparar repositórios (RQ 06)

Dados de `repos.csv`, medidos na coleta:

| Fator | Como é medido | Grupos |
|---|---|---|
| Popularidade | estrelas no momento da coleta | quartis: até 1.713 / até 3.061 / até 8.275 / acima |
| Contribuidores | contribuidores, anônimos incluídos | quartis: até 31,5 / até 77 / até 176,5 / acima |
| Idade | anos entre a criação e o fim da janela (30/9/2026) | quartis: até 2,0 / até 5,9 / até 9,8 / acima |
| Linguagem principal | campo `language` da API | as 7 linguagens com 10 ou mais repositórios, e as demais juntas em "Outras" (ver abaixo) |
| Tipo do projeto | rótulo manual (biblioteca/framework, aplicação/serviço, CLI, outro) | aplicação/serviço 26, biblioteca/framework 20, CLI 9, outro 5 (só nos 60 da amostra-ouro; ver abaixo) |
| Automação de release | arquivos de configuração e menção nos workflows (semantic-release, release-please, changesets, goreleaser) | com / sem automação: 54 / 245 |
| Conventional Commits | proporção de commits no padrão `tipo(escopo): descrição` | proporção de 0 a 1 (mediana 0,31) |

Os quartis são calculados sobre os 299 repositórios da amostra.

**Linguagem.** Os 299 repositórios têm 32 linguagens principais, mas só 7 têm
10 ou mais repositórios: TypeScript (70), Python (55), Go (35), JavaScript
(23), Java (19), Rust (19) e C++ (14). Um grupo com poucos repositórios dá teste
estatístico fraco. Por isso as 25 linguagens com menos de 10 repositórios (64
repositórios no total) foram **agrupadas em "Outras"**, e a RQ 06 compara 8
grupos: as 7 linguagens acima e "Outras".

**Tipo do projeto.** O rótulo existe só para os 60 repositórios da
amostra-ouro, não para os 299. O grupo decidiu usá-lo como fator da RQ 06
mesmo assim, **restrito a esses 60**: a comparação por tipo usa só eles, e as
comparações pelos demais fatores usam os 299. O rótulo é o consenso por
maioria dos três avaliadores (kappa de Fleiss de 0,885 nessa pergunta). Com
60 repositórios, e só 5 do tipo "outro", os testes por tipo têm pouco poder, e
cada resultado deve informar o *n* de cada grupo. Essa restrição entra nas
ameaças à validade.

### Perfil da amostra

| | Mínimo | 1º quartil | Mediana | 3º quartil | Máximo |
|---|---:|---:|---:|---:|---:|
| Estrelas | 1.009 | 1.713 | 3.061 | 8.275 | 129.050 |
| Contribuidores | 2 | 31,5 | 77 | 176,5 | 7.139 |
| Idade (anos) | 0,1 | 2,0 | 5,9 | 9,8 | 18,7 |

Por faixa de estrelas: 92 (1.000 a 2.000), 100 (2.001 a 5.000), 44 (5.001 a
10.000), 56 (10.001 a 50.000) e 7 (acima de 50.000). O dono é uma organização em
203 casos e uma pessoa em 96. O default branch é `main` em 188, `master` em 84 e
`develop` em 9.

## 5. Cobertura dos dados da amostra

Nem toda métrica existe para todo repositório. Valor ausente fica vazio no CSV,
nunca zero, e cada análise informa o seu *n*.

| Métrica | Repositórios sem o dado | Principal motivo |
|---|---:|---|
| CFR por issues de bug (`cfr_c`) | 77 de 299 | o repositório não tem issue de bug no período, ou as issues estão desativadas |
| Tempo de recuperação | 26 de 299 | nenhuma falha de CI seguida de recuperação |

A busca por issues de bug usa uma lista fixa de rótulos (`bug`, `regression`,
`type: bug`, `kind/bug`, `kind/regression`, `🐛 Bug`, `bug :bug:`). Um projeto
que marque bugs com outro rótulo aparece sem dado. Isso é uma ameaça à validade
de construto do `cfr_c`.

Além disso, 69 intervalos mensais de execuções de CI ficaram incompletos porque
a API limita o que devolve por consulta: `pytorch` (24), `dust` (15), `twenty`
(10) e `codex` (8). Isso afeta o CFR por CI desses repositórios e a seção de
Ameaças à Validade deve mencioná-lo.

## 6. Ameaças à validade ligadas à seleção

- **Externa:** a população é de repositórios com pelo menos 1.000 estrelas e
  que usam GitHub Actions. Os resultados não valem para projetos pequenos, nem
  para quem usa outro sistema de CI.
- **Viés de popularidade:** estrelas e contribuidores são medidos na data da
  coleta, não no início da janela.
- **Tipo do projeto em só 60 repositórios:** a comparação por tipo (RQ 06)
  vale para a amostra-ouro, não para os 299, e tem menos poder estatístico.
- **Amostra não estratificada:** faixas e linguagens pouco frequentes (a faixa
  acima de 50.000 estrelas tem 7 repositórios) têm pouco peso nas comparações.

## 7. Reprodução

A mesma seed (42) e os mesmos candidatos geram a mesma amostra. A busca de
candidatos depende do estado do GitHub no dia da coleta, então uma nova rodada
em outra data pode encontrar candidatos diferentes. O `config.yaml` traz
`n_repos: 300`, o mesmo valor da rodada final, então o comando do README
(`python -m pipeline --config config.yaml`) reproduz a amostra de 300.
