# Revisão da semente (S01)

Base: PLANEJAMENTO.pdf, seção 3.3. Issue: #109 (revisão), sobre a semente entregue na #104 (papel B, `seed/`, `tests/regression/`, `docs/s01/semente.md`). Revisão feita pelo papel C, que não escreveu a semente (auditoria cruzada). Todos os commits de `seed/` e `tests/regression/` são do Miguel e nenhum traz marca de assistente de código (nem `Co-Authored-By`).

## Resumo

**Aprovada com ressalva.** Estrutura, contrato de execução, arquitetura e métricas conferem com o planejamento. O que **não foi reproduzido** nesta revisão são os itens que exigem rodar a semente (build, 36 testes da semente, 29 de regressão em duas rodadas), porque o daemon do Docker estava desligado e não há Maven nesta máquina. Esses itens constam como "declarado pelo autor" e precisam de uma reprodução por quem tiver Docker antes de o piloto começar.

## Como medir

```bash
python -m metrics.coletar seed --csv --sem-archunit --sem-jdeps
```

`--sem-archunit` e `--sem-jdeps` são usados aqui porque não há Maven nem classes compiladas; com eles a medida de violações vem da verificação estática das mesmas 5 regras do `ArquiteturaTest` (testes em `tests/test_semente_real.py`).

| Métrica | Valor na semente |
|---|---|
| `arch_violations` | 0 (estática, 5 regras) |
| `cycles` | 0 |
| `doc_drift` | 0 (5 módulos, todos citados no `ARCHITECTURE.md`) |
| `max_ccn` | 4 (Lizard) |
| `dup_pct` | 1,97% (jscpd, 50 tokens e 5 linhas mínimos) |
| `loc` | 391 (Lizard nloc, só Java de `src/main`, sem comentários nem brancos) |
| `files_touched`, `modules_touched` | não se aplicam à semente isolada (são do diff de um passo) |

## Critérios de aceitação do passo 0 (seção 3.3)

| # | Critério | Resultado | Evidência |
|---|---|---|---|
| 1 | Zero violações das regras de arquitetura | **Verificado (estática)**; ArchUnit oficial não reproduzido | `arch_violations = 0`, `cycles = 0`. A verificação estática enxerga cada regra: em cópia temporária, Spring no domínio (R1), biblioteca na application (R2), controlador chamando o serviço (R5), persistência chamando `port.in` (R3) e ciclo entre `adapter.in` e `adapter.out` (R4) são detectados (`tests/test_semente_real.py`). O autor declara 5 regras, zero violações |
| 2 | 100% nos testes de regressão | **Declarado, não reproduzido** | `semente.md` declara 29 de 29 (21 HTTP, 8 interface). Contei no código 21 + 8 testes, coerente com o declarado |
| 3 | Build limpo | **Declarado, não reproduzido** | Sem Maven nem Docker aqui. `pom.xml` com Spring Boot 3.3.5 e Java 21 |
| 4 | Duas rodadas de testes idênticas | **Declarado, não reproduzido** | `semente.md` declara 29 de 29 em duas rodadas seguidas |
| 5 | Revisão por quem não a escreveu | **Feita** (esta revisão, papel C) | Ressalvas abaixo |

Os testes da própria semente são 36 (domínio 10, serviço 10, controlador 11, ArchUnit 5), contagem conferida no código.

## Contrato de execução e escopo

| # | Item | Resultado | Evidência |
|---|---|---|---|
| 6 | Stack: Java 21, Spring Boot 3, Maven, PostgreSQL em Docker | OK | `pom.xml` (Boot 3.3.5, `java.version` 21), `postgres:16` no compose |
| 7 | `docker compose up` sobe app e banco; porta 8080; `/health` 200 | OK no código; subida não reproduzida | compose com healthcheck do banco; `management...path-mapping.health=health`; `8080:8080` |
| 8 | Banco configurado só por `DATABASE_URL` | OK | `spring.datasource.url=${DATABASE_URL}`; nenhuma outra leitura de ambiente em `src/main` |
| 9 | Operações criar, listar, consultar, atualizar, concluir, excluir | OK | rotas documentadas em `semente.md`; cobertas pelos 11 testes de controlador e 21 de regressão HTTP |
| 10 | Interface mínima servida pela aplicação, sem framework, com `data-testid` | OK | `static/index.html`, `app.js`, `estilo.css`; os 16 `data-testid` listados em `semente.md` aparecem nos arquivos estáticos |
| 11 | Tamanho de 600 a 1.000 linhas | OK | `src/main` tem 734 linhas (Java 482, JS 137, CSS 77, HTML 38), conferidas por contagem. Atenção: o `loc` do esquema de dados é só Java e sem comentários (391), então **não** é comparável a essa meta |
| 12 | Sem `CLAUDE.md` na semente | OK | nenhum `CLAUDE.md` no repositório; o único `.md` em `seed/` é o `ARCHITECTURE.md` |
| 13 | Semente não escrita pelo Claude Code nem por produto da Anthropic | **Sem indício, não comprovável** | commits só do Miguel, sem trailers de assistente. O planejamento pede auditoria: o Miguel deve declarar se usou outro assistente |
| 14 | Testes nunca acessam o banco diretamente | OK | nenhuma referência a JDBC, `DataSource` ou Postgres em `tests/regression/` |
| 15 | `ARCHITECTURE.md` descreve as 5 regras | OK | as 5 regras existem como testes nomeados no `ArquiteturaTest` e estão listadas no documento |

## Ressalvas e pontos de atenção

1. **Reprodução pendente (itens 2, 3, 4 e 7).** Precisa de alguém com Docker rodando os comandos de `semente.md` ("Como rodar") e registrando a saída. Sem isso o critério de aceitação do passo 0 não está fechado.
2. **Isolamento dos testes ocultos.** `tests/regression/` fica ao lado de `seed/`. O harness (#105) precisa montar no container **só** `seed/` como workspace; se montar a raiz, o agente enxerga os testes ocultos e o experimento perde validade.
3. **`loc` ≠ meta de tamanho.** O esquema de dados mede `loc` pelo Lizard (Java, sem comentários), 391 na semente. A meta do planejamento (600 a 1.000) vale para o sistema todo, 734. Quem analisar `loc` ao longo dos passos deve saber que o ponto de partida é 391.
4. **Nome de pacote `in`.** `adapter.in` é válido em Java (`in` não é palavra reservada) e a semente o usa. Os scripts de métricas reconhecem a camada pelos segmentos `web`/`persistence`, então funcionam, e o módulo medido é `adapter.in` / `adapter.out`.
5. **Regras de arquitetura mais rígidas que o planejamento.** A regra 5 da semente proíbe também `application.service`, `port.out`, Spring Data e JPA nos adaptadores de entrada, e a regra 3 proíbe a saída de usar `port.in` e `service`. É mais forte que "controladores não acessam repositórios", o que é bom para detectar deriva, e a verificação estática foi alinhada a elas.
6. **Neutralidade em relação a P1 a P4.** A semente não tem relógio injetável, filtros, ordenação, paginação, empresa nem importação, como diz o `semente.md`. Já existe ordenação por criação na listagem, que não interfere em P2 (ordenação por vencimento).

## Veredito

**Aprovada com ressalva.** Nenhuma correção de código é exigida do papel B. Pendências, nesta ordem: (a) reproduzir build e as duas rodadas de testes com Docker e anexar a saída; (b) o Miguel declarar o uso de assistente na escrita da semente; (c) garantir no harness que só `seed/` vira workspace.
