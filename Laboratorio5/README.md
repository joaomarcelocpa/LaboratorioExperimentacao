# Laboratório 5: deterioração do código produzido pelo Claude Code

Experimento controlado em software real (Claude Code) sobre a deterioração do código em pedidos consecutivos de comportamento: modo incremental × regenerado, medido de 0 a 10 passos. Planejamento completo em `PLANEJAMENTO.pdf`. Este repositório de código cobre, na Sprint 1, o **papel C (Análise e Impacto)**: pipeline de análise, esquema de dados, simulação de poder e métricas estruturais.

## Como rodar

Com Python 3 (testado com 3.15), na pasta `Laboratorio5/`:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

| Comando | O que faz |
|---|---|
| `python -m analysis.run --sintetico` | Gera dados sintéticos em `data/synthetic/` e roda toda a análise em `results/sintetico/` |
| `python -m analysis.run --entrada data/pilot/passos.csv` | A mesma análise sobre o CSV do piloto ou da coleta (mesmo formato) |
| `python -m analysis.pilot data/pilot/passos.csv` | Tabela dos 5 critérios do piloto (seção 3.12) e sugestão de decisão |
| `python -m analysis.power` | Simulação de poder (número de cadeias por modo) em `results/power/` |
| `python -m metrics.coletar <workspace> --csv` | As 8 métricas estruturais de um workspace Java |
| `python -m pytest` | Testes automatizados |

As métricas usam ferramentas externas: `jdeps` (JDK), `jscpd` (via `npx`, precisa de Node) e, para o ArchUnit oficial, `mvn`. Sem o Maven, `metrics.coletar` usa a verificação estática das mesmas 5 regras e informa a fonte usada (`--sem-jscpd`, `--sem-archunit` e `--sem-jdeps` desligam cada uma). O Lizard é instalado pelo `requirements.txt`.

Todas as simulações usam `numpy.random.default_rng(42)`.

## Estrutura

```
analysis/   esquema do CSV, gerador sintético, modelos, sobrevivência, poder, critérios do piloto, pipeline
metrics/    métricas estruturais de um workspace (ArchUnit, jdeps, Lizard, jscpd, localidade, deriva documental)
docs/s01/   plano de análise, esquema de dados, simulação de poder, revisão da semente, relatório do piloto
tests/      testes automatizados (fixtures Java hexagonais mínimas)
data/       dados (sintéticos aqui; piloto e coleta na pasta própria)
results/    tabelas e figuras geradas
```

## Estado da Sprint 1 (papel C)

- Plano de análise, esquema de dados e simulação de poder: prontos (`docs/s01/`).
- Pipeline `analysis/`: roda de ponta a ponta com dados sintéticos; roda com o piloto sem mudar o formato.
- Scripts de métricas: prontos e testados sobre fixtures; ainda sem a semente real (depende da entrega do papel B).
- Revisão da semente e relatório do piloto: roteiros prontos, **conteúdo pendente** da semente e dos dados do piloto.
