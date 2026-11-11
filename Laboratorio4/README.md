# Laboratório de Medição e Experimentação de Software
## Laboratório 4: testes de hipótese por dentro

Compara o **t de Welch** e o **Mann-Whitney** no tempo até o merge de PRs revisados por bots de revisão e por pessoas, usando dados reais do dataset AIDev e simulação de Monte Carlo.

## Como rodar

O dashboard é uma página HTML única, `dashboard.html`, na raiz da pasta. Ela já vem pronta no repositório: basta abrir o arquivo no navegador (duplo clique), sem servidor e sem instalar nada.

Para regenerar a página a partir dos dados e abri-la, com Python 3 instalado, na pasta do projeto:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -m src.painel --abrir
```

Nas próximas vezes basta ativar o ambiente e rodar o último comando:

```bash
source .venv/bin/activate && python -m src.painel --abrir
```

## Como reproduzir os resultados

Todas as simulações usam `numpy.random.default_rng(42)`, então os resultados se repetem.

| Comando | O que gera |
|---|---|
| `python src/coletar_dados.py <pasta do AIDev>` | `data/raw/prs.csv` (60 PRs reais) |
| `python -m src.gerador` | G1 em `results/figures/` |
| `python -m src.g2` | G2 em `results/figures/` |
| `python -m src.testes` | os dois testes em um conjunto simulado |
| `python -m src.simulacao` | Q1 em `data/simulated/q1_erro_tipo_i.csv` |
| `python -m src.q2` | Q2 em `data/simulated/q2_poder.csv` |
| `python -m src.q3` | Q3 em `data/simulated/q3_situacoes.csv` |
| `python -m src.g3_g4` | G3 e G4 em `results/figures/` |
| `python -m src.painel` | `dashboard.html`, com todos os dados embutidos |
| `python -m pytest` | testes automatizados |

O `data/raw/prs.csv` já está no repositório, então o primeiro comando só é necessário para refazer a amostra (a origem está em `data/raw/FONTE.md`).

## Estrutura

```
dashboard.html    dashboard (página única, gerada por src/painel.py)
src/              gerador, testes, G2, motor de simulação, painel
data/raw/         dados reais e fonte
data/simulated/   resultados das simulações
results/figures/  gráficos G1 a G4
docs/             cenário, interpretação e guia da sprint
tests/            testes automatizados
```
