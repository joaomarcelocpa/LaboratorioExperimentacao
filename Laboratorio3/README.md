# Laboratório de Medição e Experimentação de Software
## Laboratório 3 — Mineração de métricas DORA

Pipeline que coleta dados públicos de repositórios open-source do GitHub e
calcula as quatro métricas DORA: deployment frequency, lead time for changes,
change failure rate e tempo de recuperação.

A coleta é feita por script próprio, via API REST do GitHub com `requests` —
o enunciado proíbe bibliotecas prontas de acesso à API.

## Requisitos

- Python 3.12
- Um token do GitHub (*personal access token*, escopo `public_repo`)
- Opcional: Docker e `make`

## Configuração

```bash
cp .env.example .env     # preencha GITHUB_TOKEN
pip install -r requirements.txt
```

O token é lido da variável de ambiente `GITHUB_TOKEN` **ou** do arquivo `.env`
na pasta onde o comando roda (o pipeline carrega o `.env` sozinho; uma variável
já definida no shell tem prioridade). Ele **nunca** é commitado. Sem ele, só
respostas que já estão em cache funcionam. No Docker, o `make run-docker` passa
o `.env` ao container com `--env-file`.

No PowerShell:

```powershell
$env:GITHUB_TOKEN = "seu_token_aqui"
```

## Rodar

Com `make`:

| Comando | O que faz |
|---|---|
| `make test` | testes com cobertura mínima de 80% |
| `make run` | roda a coleta a partir do `config.yaml` |
| `make contrato` | regenera o dicionário de dados e falha se tiver mudado |
| `make run-docker` | constrói a imagem e roda a coleta no container |
| `make reproduce` | esqueleto; completa na S03 |

**Sem `make`** (Windows, PowerShell — nem o Windows padrão nem o Git Bash
trazem `make`):

```powershell
pytest --cov=metricas --cov=coleta --cov-report=term-missing --cov-fail-under=80
python -m pipeline --config config.yaml
python -m metricas.dicionario
docker build -t lab03-dora .
docker run --rm -e GITHUB_TOKEN -v "${PWD}/data:/app/data" lab03-dora --config config.yaml
```

## Comando único

```bash
export GITHUB_TOKEN=...        # nunca commitado; veja "Configuração"
python -m pipeline --config config.yaml              # amostra de n_repos (100)
python -m pipeline --config config.yaml --limite 10  # rodada curta de medição
```

O comando faz tudo: busca fatiada de candidatos, filtros e funil, sorteio com
semente fixa, coleta (releases, commits entre releases, deployments, workflow
runs, issues de bug, metadados) e cálculo das métricas. `--limite N` troca o
`n_repos` do config **antes** do sorteio, então `funil.csv` fecha com N.

Um repositório que falha é registrado e os demais seguem; o resumo no fim da
execução lista quem falhou. A coleta recusa rodar com a janela ainda marcada
como `placeholder: true`.

### Saídas (`data/processed/`)

| Arquivo | O que é |
|---|---|
| `candidatos.csv` | candidatos da busca fatiada, já sem forks, arquivados e duplicatas |
| `funil.csv` | por etapa: entraram, saíram e motivo; a soma fecha na amostra final |
| `descartes.csv` | cada repositório descartado, com etapa e motivo |
| `repos.csv` | metadados e fatores de release da amostra |
| `releases.csv`, `tags.csv` | releases (sem draft) e tags com data do commit |
| `releases_ignoradas.csv` | releases sem comparação possível (sem anterior, 404) |
| `commits.csv` | commits entre releases consecutivas |
| `deployments.csv` | deployments em ambientes de produção |
| `runs.csv`, `run_attempts.csv` | workflow runs de push no default branch e tentativas anteriores |
| `episodios.csv` | episódios de falha do CI, com censura e flag de só-flaky |
| `issues_bug.csv` | issues de bug (sem PRs) com a tag citada |
| `metricas.csv` | uma linha por repositório: as métricas DORA e seus proxies |
| `metricas_mensais.csv` | CFR de CI e recuperação por repositório e mês (RQ 08b) |
| `custo_api.csv` | chamadas por endpoint: as que saíram da máquina e as do cache |
| `custo_selecao.csv` | diagnóstico: custo só da seleção (busca e filtros), que não cresce com a amostra |
| `fatias_saturadas.csv` | só se existir: fatias que bateram o teto de 1.000 resultados |

As colunas de cada arquivo estão em
[docs/dicionario_dados.md](docs/dicionario_dados.md). Métrica sem dado vale
vazio (NaN), nunca zero.

### Planejando uma coleta maior

Depois de uma rodada curta, estime o custo para 300 repositórios a partir do
`custo_api.csv` e do tempo medido (extrapolação linear, ordem de grandeza):

```bash
python -m pipeline.estimativa --medido 10 --segundos 600 --alvo 300
```

A seleção percorre todos os candidatos qualquer que seja o `--limite`, então
seu custo é fixo: a estimativa lê `custo_selecao.csv` e só escala o resto.
Passe `--segundos-selecao` (impresso no fim da seleção) para tratar o tempo
do mesmo jeito.

**Limitação da retomada:** o cache guarda respostas 2xx e 404. Respostas
403, 422 e 410 (Actions indisponível, fatia recusada, issues desligadas) não
são guardadas e se repetem a cada rodada, então a segunda rodada pode ter
`chamadas > 0` em alguns endpoints. `custo_api.csv` conta só a execução atual.

## Cache e retomada

Toda resposta da API é guardada em `data/raw/cache.sqlite`, com chave
método + URL + parâmetros. **Interromper a coleta e rodar de novo não repete
chamadas já feitas** — inclusive as que deram 404.

O token não entra na chave, então o cache de um integrante serve aos outros.
`data/raw/` está no `.gitignore`.

O cliente HTTP também cuida sozinho do rate limit (dorme até o `Reset` quando
restam menos de 50 chamadas, respeita `Retry-After`) e repete erros 5xx com
espera de 1, 2, 4, 8 e 16 segundos.

`data/processed/custo_api.csv` registra, por endpoint, quantas chamadas
saíram da máquina e quantas foram servidas pelo cache.

## Fatias saturadas

A API devolve no máximo 1.000 resultados por consulta filtrada. A coleta de
workflow runs fatia a janela em meses e parte ao meio toda fatia que bate esse
teto — mês vira quinzena, quinzena vira semana, e assim por diante. A
bissecção para quando a fatia já dura uma hora ou menos (na prática as
menores ficam entre 39 e 44 minutos, porque o corte é sempre ao meio), ou
antes disso, se dividir deixar de estreitar o resultado.

`data/processed/fatias_saturadas.csv` (`repo`, `inicio`, `fim`, `total_count`)
registra as fatias que bateram o teto mesmo no piso, ou que a API recusou
subdividir. **Parte dos runs daquele intervalo ficou de fora**, então o
arquivo é ameaça à validade e precisa ser reportado no artigo.

Ele é diagnóstico, não dataset de análise: não aparece em
`docs/dicionario_dados.md` nem passa pelo validador de contratos.

## Estrutura

```
pipeline/        orquestração e leitura do config
coleta/          http.py (cliente, cache, rate limit, paginação), coletores
metricas/        schemas.py (contratos), dicionario.py, funções das RQs
tests/           pytest, sem rede: responses + fixtures à mão
data/raw/        cache.sqlite (não versionado)
data/processed/  CSVs do estudo
docs/            dicionario_dados.md (gerado dos schemas)
```

Cada coluna de cada CSV está documentada em
[docs/dicionario_dados.md](docs/dicionario_dados.md), gerado de
`metricas/schemas.py`.

## Configuração do estudo

`config.yaml` traz a janela de observação, as faixas de estrelas da busca
fatiada, os limites de inclusão (≥ 5 releases, ≥ 50 runs) e a semente do
sorteio. A coleta se recusa a rodar enquanto a janela estiver marcada como
`placeholder: true`.
