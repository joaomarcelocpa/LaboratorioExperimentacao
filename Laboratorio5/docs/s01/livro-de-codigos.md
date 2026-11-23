# Livro de códigos — decisões arquiteturais do agente (rascunho)

**Status:** rascunho da S01, definido antes de olhar qualquer dado do piloto ou da coleta.
**Finalidade:** codificar as decisões de implementação tomadas pelo Claude Code em cada execução,
para permitir análise qualitativa e cálculo de concordância entre avaliadores (kappa).

---

## Instrução para avaliadores

Leia o diff do commit gerado pelo agente em cada passo. Para cada categoria abaixo, atribua um
código ao commit. Quando mais de um código da mesma categoria se aplicar, registre todos,
separados por vírgula. Registre dúvidas na coluna "Observação" — elas serão resolvidas em
reunião antes do fechamento da coleta.

Regra de ouro: codifique o que o diff **mostra**, não o que você acha que o agente pretendia.

---

## Categoria 1 — Localização da mudança (onde o código novo foi colocado)

| Código | Definição | Exemplo |
|---|---|---|
| LOC-DOM | Mudança no pacote de domínio | Nova regra de negócio em `Tarefa.java` |
| LOC-APP | Mudança no pacote de aplicação (casos de uso, portas) | Novo caso de uso em `port.in` |
| LOC-WEB | Mudança no adaptador de entrada (web/HTTP) | Novo endpoint em `TarefaController` |
| LOC-PER | Mudança no adaptador de saída (persistência) | Nova query no repositório JPA |
| LOC-CFG | Mudança em configuração ou composição | Novo bean em `Montagem.java` |
| LOC-INF | Mudança em infraestrutura (migration SQL, Docker, pom.xml) | Nova coluna em `V2__...sql` |
| LOC-FRO | Mudança no front-end (HTML, JS, CSS) | Novo campo em `index.html` |
| LOC-TST | Mudança ou adição de testes pelo agente | Novo `@Test` escrito pelo agente |
| LOC-DOC | Mudança no `ARCHITECTURE.md` | Atualização da lista de pacotes |

---

## Categoria 2 — Conformidade estrutural (respeito à arquitetura hexagonal declarada)

| Código | Definição |
|---|---|
| EST-OK | Nenhuma violação das regras do `ARCHITECTURE.md` introduzida |
| EST-DEP | Dependência proibida criada (ex.: `domain` importa Spring; controlador acessa repositório) |
| EST-CIC | Ciclo de dependência introduzido |
| EST-DOC | Módulo ou regra nova não documentada no `ARCHITECTURE.md` |
| EST-INV | Inversão de dependência ausente onde a arquitetura exigiria (porta não criada) |

---

## Categoria 3 — Estratégia de implementação do novo comportamento

| Código | Definição |
|---|---|
| EST-INC | Implementação incremental sobre o código existente (adiciona, estende) |
| EST-REF | Refatoração de código existente antes ou junto da adição |
| EST-REW | Reescrita de trecho existente sem preservar a lógica anterior |
| EST-DUP | Duplicação de lógica existente em vez de reutilizá-la |
| EST-ABR | Abstração nova criada (interface, classe base, utilitário genérico) |

---

## Categoria 4 — Gestão de testes

| Código | Definição |
|---|---|
| TST-NEN | O agente não criou nem modificou testes |
| TST-ACE | O agente escreveu testes de aceitação do próprio pedido |
| TST-REG | O agente escreveu ou modificou testes de regressão existentes |
| TST-DEL | O agente deletou ou comentou testes existentes |
| TST-FLK | O agente adicionou `@Disabled`, `@Ignore` ou equivalente em testes |

---

## Categoria 5 — Conformidade documental

| Código | Definição |
|---|---|
| DOC-OK | `ARCHITECTURE.md` reflete o estado do código após o commit |
| DOC-LAG | Módulo ou regra nova no código não está no `ARCHITECTURE.md` |
| DOC-INV | `ARCHITECTURE.md` descreve algo que o código não implementa mais |
| DOC-NOP | `ARCHITECTURE.md` não foi tocado (neutro — combinar com DOC-OK ou DOC-LAG) |

---

## Notas de calibração

- Antes de codificar os dados reais, os dois avaliadores codificam independentemente uma
  subamostra de ~20% das execuções do piloto e calculam o kappa de Cohen.
- Se kappa < 0,60, a categoria com menor concordância é revisada e as definições são refinadas.
- O livro de códigos final (pós-calibração) substitui este rascunho e é versionado como
  `docs/s02/livro-de-codigos-final.md`.
