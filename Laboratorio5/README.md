# Laboratório de Medição e Experimentação de Software
## Laboratório 5: deterioração do código produzido pelo Claude Code

Experimento controlado em software real (Claude Code) sobre a deterioração do código em pedidos consecutivos de comportamento: modo incremental × regenerado, medido de 0 a 10 passos. Planejamento completo em `PLANEJAMENTO.pdf`. Este repositório de código cobre, na Sprint 1, o **papel C (Análise e Impacto)**: pipeline de análise, esquema de dados, simulação de poder e métricas estruturais.

## Como rodar

Com Python 3 (testado com 3.15), na pasta `Laboratorio5/`:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

| Comando | O que faz |
|---|---|
| `python -m analysis.run --sintetico` | Gera dados sintéticos em `data/synthetic/` e roda toda a análise em `results/sintetico/` (subpastas `descritiva/`, `figures/`, `modelos/`, `sobrevivencia/`, `diferenca-pareada/` e `testes_holm.csv`) |
| `python -m analysis.run --entrada data/pilot/passos.csv` | A mesma análise sobre o CSV do piloto ou da coleta (mesmo formato); na coleta completa, `--saida results` grava em `results/descritiva/` etc. |
| `python -m analysis.pilot data/pilot/passos.csv` | Tabela dos 5 critérios do piloto (seção 3.12) e sugestão de decisão |
| `python -m analysis.power` | Simulação de poder (número de cadeias por modo) em `results/power/` |
| `python -m metrics.coletar <workspace> --csv` | As 8 métricas estruturais de um workspace Java |
| `python -m pytest` | Testes automatizados |

As métricas usam ferramentas externas: `jdeps` (JDK), `jscpd` (via `npx`, precisa de Node) e, para o ArchUnit oficial, `mvn`. Sem o Maven, `metrics.coletar` usa a verificação estática das mesmas 5 regras e informa a fonte usada (`--sem-jscpd`, `--sem-archunit` e `--sem-jdeps` desligam cada uma). O Lizard é instalado pelo `requirements.txt`.

Todas as simulações usam `numpy.random.default_rng(42)`.

## Estrutura

```
analysis/   esquema do CSV, gerador sintético, descritiva, figuras, modelos, sobrevivência, poder, critérios do piloto, pipeline
metrics/    métricas estruturais de um workspace (ArchUnit, jdeps, Lizard, jscpd, localidade, deriva documental)
docs/s01/   plano de análise, esquema de dados, simulação de poder, revisão da semente, relatório do piloto
seed/       semente do experimento (papel B)
tests/      testes automatizados do pipeline e das métricas; tests/regression é a suíte de regressão (papel B)
data/       dados (sintéticos aqui; piloto e coleta na pasta própria)
results/    tabelas e figuras geradas
```

## Estado da Sprint 1 (papel C)

- Plano de análise, esquema de dados e simulação de poder: prontos (`docs/s01/`).
- Pipeline `analysis/`: roda de ponta a ponta com dados sintéticos; roda com o piloto sem mudar o formato.
- Scripts de métricas: prontos e testados sobre fixtures e sobre a semente real (`seed/`), inclusive com violações injetadas.
- Revisão da semente: feita, aprovada com ressalva (pendente reproduzir build e testes com Docker). Ver `docs/s01/revisao-da-semente.md`.
- Relatório do piloto: roteiro pronto, **conteúdo pendente** dos dados do piloto (#105).
