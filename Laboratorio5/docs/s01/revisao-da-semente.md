# Revisão da semente (S01)

Base: PLANEJAMENTO.pdf, seção 3.3. Issue: #109 (revisão), com a semente produzida na #104 (papel B).

> **Status: pendente.** A semente (issue #104, Miguel) ainda não foi entregue no repositório, então **nenhum item abaixo foi verificado**. Este arquivo é o roteiro de revisão, com as medições já automatizadas. Preencha a coluna "Resultado" quando a semente existir e troque este aviso pelo veredito. Regra de auditoria cruzada: quem escreve a semente não a revisa (papel C revisa a semente do papel B).

## Como medir a semente

Com o workspace da semente em uma pasta (commitada, `src/main/java`, `ARCHITECTURE.md`):

```bash
python -m metrics.coletar <workspace> --csv
```

Isso devolve as colunas `arch_violations, cycles, files_touched, modules_touched, max_ccn, dup_pct, loc, doc_drift`. Para a semente, o resultado esperado de `arch_violations`, `cycles` e `doc_drift` é **zero**.

## Critérios de aceitação do passo 0 (seção 3.3)

| # | Critério | Como verificar | Resultado | Evidência |
|---|---|---|---|---|
| 1 | Zero violações das regras de arquitetura | `arch_violations = 0` em `metrics.coletar` (e `mvn test` do teste ArchUnit) | pendente | — |
| 2 | 100% nos testes de regressão | Suíte HTTP e de interface sobre `docker compose up`; `reg_failed = 0` | pendente | — |
| 3 | Build limpo | `mvn -B package` sem erro nem aviso relevante | pendente | — |
| 4 | Duas rodadas de testes idênticas | Duas execuções da suíte completa; `flaky = 0` | pendente | — |
| 5 | Revisão por quem não a escreveu | Esta revisão (papel C) | pendente | — |

## Contrato de execução e escopo (seção 3.3)

| # | Item | Resultado |
|---|---|---|
| 6 | Stack: Java 21, Spring Boot 3, Maven, PostgreSQL em Docker | pendente |
| 7 | `docker compose up` sobe aplicação e PostgreSQL; porta 8080; `GET /health` responde 200 | pendente |
| 8 | Banco configurado só por `DATABASE_URL` | pendente |
| 9 | Operações: criar, listar, consultar, atualizar, concluir e excluir tarefa (título, descrição, responsável, vencimento com data e hora, status) | pendente |
| 10 | Interface web mínima (lista e formulário) servida pela própria aplicação, sem framework de front-end, com `data-testid` | pendente |
| 11 | Tamanho: 600 a 1.000 linhas (`loc` de `metrics.coletar`, Lizard nloc de `src/main`) | pendente |
| 12 | Sem `CLAUDE.md` na semente | pendente |
| 13 | A semente não foi escrita pelo Claude Code nem por outro produto da Anthropic (registro da autoria e do uso de assistente) | pendente |
| 14 | Testes nunca acessam o banco diretamente (só endpoints) | pendente |
| 15 | `ARCHITECTURE.md` descreve as 5 regras verificáveis (domain, application, entrada × saída, sem ciclos, controladores × repositórios) | pendente |

## Checagem cruzada do `ARCHITECTURE.md` com as métricas

As regras de arquitetura estão implementadas de forma estática em `metrics/arquitetura.py` (R1 a R5, espelho das 5 regras do planejamento) e servem de conferência independente do ArchUnit da semente: se `arch_violations` (ArchUnit) e a verificação estática discordarem na semente, uma das duas regras está mal escrita e isso deve ser resolvido **antes do piloto**.

Pontos que a verificação estática assume e o documento da semente precisa deixar explícitos:

- Nomes de pacotes por camada: `domain`, `application` e adaptadores de entrada/saída com os segmentos `web`/`rest` e `persistence`/`jpa` (lista em `metrics/java.py`). `in` é palavra reservada de Java, então não existe pacote `adapter.in`.
- R2 é literal: `application` depende só de `domain` e do JDK, o que **proíbe anotações Spring na camada de aplicação**. Se a semente usa `@Service` ali, ou a regra do ARCHITECTURE.md ou o código deve mudar.

## Veredito

Pendente (semente não entregue). Registrar aqui: aprovada, aprovada com ressalvas ou reprovada, com a lista de correções pedidas ao papel B.
