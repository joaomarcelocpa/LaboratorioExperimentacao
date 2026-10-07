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

O token é lido da variável de ambiente `GITHUB_TOKEN` e **nunca** é commitado.
Sem ele, só respostas que já estão em cache funcionam.

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
