# Orientação para a replicação cruzada

Este documento é para o **grupo replicador**: quem recebeu este pipeline no
sorteio da entrega final e precisa reproduzi-lo (seção 9 da especificação).
Siga só o que está aqui e no [README](../README.md). Se algo travar, **não peça
ajuda ao grupo autor**: registre o problema, porque ele é um resultado do
estudo e vira uma Issue neste repositório.

## 1. O que o grupo replicador entrega

1. Executar o pipeline sobre uma **subamostra de 30 repositórios**.
2. Comparar os valores obtidos com os CSVs originais: diferença relativa por
   métrica e % de repositórios com a mesma classificação DORA.
3. Abrir **Issues neste repositório** para cada problema encontrado.
4. Relatar o resultado na seção "Replicação cruzada" do artigo.

## 2. Preparação

Requisitos: Python 3.12 (ou Docker) e um token do GitHub com escopo
`public_repo`.

```bash
git clone <url deste repositório>
cd LaboratorioExperimentacao/Laboratorio3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GITHUB_TOKEN=seu_token     # nunca commite o token
```

Sem Python instalado, use o Docker:

```bash
docker build -t lab03-dora .
```

Antes de coletar, confirme que o ambiente está são:

```bash
pytest --cov=metricas --cov=coleta --cov-fail-under=80   # esperado: tudo verde, cobertura ≥ 80%
python -m metricas.dicionario && git diff --exit-code docs/dicionario_dados.md
```

Se algum desses falhar, abra uma Issue com o comando e a saída completa.

## 3. Executar a subamostra de 30 repositórios

O `config.yaml` traz a janela de observação (2025-10-01 a 2026-09-30), as
faixas de estrelas, os limites de inclusão e a semente (`seed: 42`). **Não os
altere**: replicar com outra janela ou semente deixa de ser replicação.

```bash
python -m pipeline --config config.yaml --limite 30
```

ou, com Docker:

```bash
docker run --rm -e GITHUB_TOKEN -v "$PWD/data:/app/data" lab03-dora --config config.yaml --limite 30
```

Para não sobrescrever os CSVs originais que vêm no repositório, **copie
antes** a pasta de referência:

```bash
cp -r data/processed data/processed_original
```

O que esperar:

- Os candidatos são examinados em ordem aleatória fixada pela semente, e o
  exame para quando `--limite` repositórios são aprovados. Com a mesma semente
  e os mesmos candidatos, os 30 primeiros aprovados são os **30 primeiros da
  amostra original**.
- A busca de candidatos é feita ao vivo na API. Se o número de estrelas dos
  repositórios mudou desde a coleta original, a lista de candidatos pode ser
  um pouco diferente e a subamostra pode não coincidir 100% com a original.
  Compare apenas os repositórios que aparecem nos dois lados (seção 4) e
  registre quantos ficaram de fora.
- A coleta é longa por causa da cota da API (5.000 chamadas por hora). O
  pipeline espera sozinho quando a cota acaba. Interromper com Ctrl-C e rodar
  de novo **continua do cache**, sem repetir chamadas.
- `python -m pipeline.estimativa --medido 10 --segundos <tempo> --alvo 30`
  estima o custo a partir de uma rodada curta.
- Um repositório que falha é registrado e os demais seguem. O resumo no fim
  da execução lista quem falhou. Anote esses casos.

## 4. Comparar com o resultado original

Os arquivos que importam estão em `data/processed/`: `metricas.csv` (uma linha
por repositório) e `funil.csv`. O dicionário de cada coluna está em
[dicionario_dados.md](dicionario_dados.md).

```python
import pandas as pd

orig = pd.read_csv("data/processed_original/metricas.csv").set_index("repo")
novo = pd.read_csv("data/processed/metricas.csv").set_index("repo")

comuns = orig.index.intersection(novo.index)
print(f"repositórios em comum: {len(comuns)} de {len(novo)}")

metricas = ["freq_release", "lt_release_h", "cfr_a", "recuperacao_h"]
for m in metricas:
    o, n = orig.loc[comuns, m], novo.loc[comuns, m]
    rel = ((n - o).abs() / o.abs().replace(0, float("nan"))).median()
    print(f"{m}: diferença relativa mediana = {rel:.1%}")

mesma = (orig.loc[comuns, "classe_dora"] == novo.loc[comuns, "classe_dora"]).mean()
print(f"mesma classe DORA: {mesma:.1%}")
```

Pontos de atenção na comparação:

- **Métrica vazia não é zero.** Valor ausente (NaN) significa "sem dado". Não
  o compare como se fosse 0.
- **Diferenças pequenas são esperadas.** Os repositórios continuam recebendo
  commits, as releases podem ser editadas e a data de coleta é outra. Releases
  e runs dentro da janela fixa mudam pouco, mas mudam. Explique as diferenças
  em vez de só reportá-las.
- **Runs incompletos.** `fatias_saturadas.csv` lista intervalos em que a API
  bateu o teto de 1.000 resultados e parte dos runs ficou de fora. Isso afeta
  CFR de CI e tempo de recuperação desses repositórios (veja "Limitações
  conhecidas" no README). Divergência nessas métricas nesses repositórios
  tem explicação conhecida e não é erro de replicação.
- **Arquivos grandes.** `commits.csv.gz` e `runs.csv.gz` abrem direto no
  `pandas.read_csv`. O gzip é determinístico, então coletas idênticas geram
  bytes idênticos.

## 5. Como abrir uma Issue

Abra uma Issue **neste repositório** para cada problema distinto. Use um dos
três tipos e inclua sempre as evidências abaixo.

| Tipo | Quando |
|---|---|
| Falha de execução | o comando quebrou, travou ou pediu algo não documentado |
| Documentação faltante | o README ou o dicionário de dados não bastou para seguir |
| Divergência de resultado | um valor ou classificação diferiu além do esperado |

Modelo:

```
Título: [execução|documentação|divergência] resumo em uma linha

Ambiente: sistema operacional, versão do Python (ou Docker), data da execução
Comando executado:
Mensagem de erro (completa):
Valor esperado (CSV original) x valor obtido:
Repositório(s) afetado(s):
O que já foi tentado:
```

Uma Issue por problema, para o grupo autor poder responder e fechar cada uma
separadamente.

## 6. Registro no artigo

Na seção "Replicação cruzada", responda:

1. O estudo foi reproduzível apenas com o README? Em que passos foi preciso
   improvisar?
2. Quantos dos 30 repositórios coincidiram com os da amostra original?
3. Qual a diferença relativa mediana por métrica e qual o % de repositórios
   com a mesma classe DORA?
4. Que diferenças foram explicadas (coleta em outra data, runs incompletos) e
   quais ficaram sem explicação?
5. Quais Issues foram abertas e quais já foram respondidas?

## 7. Checklist rápido

- [ ] Clone limpo, sem `.env`, sem cache, sem ajuda do grupo autor
- [ ] `pytest` verde e `make contrato` sem diferença
- [ ] `data/processed` copiado para `data/processed_original` antes de coletar
- [ ] `python -m pipeline --config config.yaml --limite 30` concluído (anote o tempo)
- [ ] Comparação feita só sobre os repositórios em comum
- [ ] Uma Issue por problema, com comando, erro e valores esperado x obtido
- [ ] Seção "Replicação cruzada" do artigo preenchida
