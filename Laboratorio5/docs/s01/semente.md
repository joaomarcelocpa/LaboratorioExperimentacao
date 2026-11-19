# Semente do Lab05 (passo 0)

A semente é o instrumento do experimento: um sistema pequeno, com arquitetura documentada, sobre o qual o Claude Code recebe pedidos consecutivos. Não é o objeto da pesquisa. Ela foi feita para ser correta, estável e **neutra**: não antecipa nenhum dos pedidos P1 a P4.

## Domínio

Gerenciador de tarefas. Uma tarefa tem `id` (UUID), `titulo` (obrigatório, até 120), `descricao` (opcional, até 2.000), `responsavel` (obrigatório, até 80), `vencimento` (data e hora, guardado em UTC), `status` (`PENDENTE` ou `CONCLUIDA`) e `criadaEm`.

Operações: criar, listar, consultar, atualizar, concluir e excluir. A listagem vem ordenada por criação. Concluir é idempotente.

### API

| Operação | Rota | Sucesso | Erros |
|---|---|---|---|
| Criar | `POST /tarefas` | 201 + `Location` | 400 |
| Listar | `GET /tarefas` | 200 | |
| Consultar | `GET /tarefas/{id}` | 200 | 404 |
| Atualizar | `PUT /tarefas/{id}` | 200 | 400, 404 |
| Concluir | `POST /tarefas/{id}/concluir` | 200 | 404 |
| Excluir | `DELETE /tarefas/{id}` | 204 | 404 |
| Saúde | `GET /health` | 200 | |

Erros: `{"erro":"requisicao_invalida|nao_encontrada","mensagem":"..."}`. `id` que não é UUID dá 404. `vencimento` aceita offset (`-03:00`) e volta normalizado em UTC (`Z`). `PUT` não muda o `status`.

### Interface

Página única servida pela aplicação (`static/index.html`, `app.js`, `estilo.css`), sem framework. `data-testid`: `lista-tarefas`, `tarefa-item`, `tarefa-titulo`, `tarefa-responsavel`, `tarefa-vencimento`, `tarefa-status`, `form-titulo`, `form-descricao`, `form-responsavel`, `form-vencimento`, `form-salvar`, `form-cancelar`, `form-erro`, `botao-editar`, `botao-concluir`, `botao-excluir`. Todo texto do usuário entra na página por `textContent`.

## Decisões

Vêm do planejamento (seções 3.2 e 3.3): Java 21, Spring Boot 3, Maven, PostgreSQL, arquitetura hexagonal, regras ArchUnit, contrato de execução, interface mínima com `data-testid`, sem `CLAUDE.md`.

Decisões de implementação (mais detalhes em `docs/superpowers/specs/2026-11-18-semente-design.md`):

- `application` sem anotações Spring; `config` monta o serviço e registra o escaneamento JPA.
- Entidade JPA separada do modelo de domínio, com mapeamento no adaptador.
- Esquema por Flyway (`V1__tarefa.sql`), `ddl-auto=validate`, sem índices além da chave primária.
- `DATABASE_URL` no formato JDBC com credenciais; `/health` pelo Spring Actuator mapeado em `/health`.
- `Tarefa` trunca `vencimento` e `criadaEm` a microssegundos, porque o PostgreSQL guarda microssegundos.
- Respostas JSON entregam datas como texto ISO-8601 em UTC.
- Portas de entrada com um método próprio cada (`criar`, `listar`, `consultar`, `atualizar`, `concluir`, `excluir`).

## O que fica de fora de propósito

Relógio injetável, filtros, ordenação, paginação, índices extras, noção de empresa ou usuário, avisos, importação de arquivos, processamento assíncrono.

## Como rodar

Subir a semente (em `Laboratorio5/seed`):

```
docker compose up -d --build
```

Testes da semente (domínio, serviço, controlador e ArchUnit), sem JDK local:

```
docker run --rm -v "<caminho>/seed:/w" -w /w maven:3.9-eclipse-temurin-21 mvn -B test
```

Testes de regressão (HTTP e interface): ver `tests/regression/README.md`.

## Estado verificado

- Testes da semente: 36 (domínio 10, serviço 10, controlador 11, ArchUnit 5), todos passando.
- ArchUnit: 5 regras, zero violações. A regra 1 foi testada com uma violação injetada e falhou como esperado; revertida em seguida.
- Regressão: 22 testes (16 HTTP, 6 interface), 22 de 22 em duas rodadas seguidas, sem acesso ao banco. Com a aplicação parada, os 22 falham.
- Tamanho de `src/main`: 734 linhas (Java 482, JS 137, CSS 77, HTML 38).
