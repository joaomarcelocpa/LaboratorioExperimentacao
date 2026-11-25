# Livro de códigos — decisões arquiteturais do agente (versão final)

**Status:** versão final, congelada antes de abrir os dados da coleta completa.
**Finalidade:** codificar as decisões de implementação tomadas pelo Claude Code em cada execução,
para análise qualitativa e cálculo de concordância entre avaliadores (kappa de Cohen).
**Origem:** evolução do rascunho `docs/s01/livro-de-codigos.md`, refinado após a calibração no piloto.

---

## O que é uma "decisão"

Uma **decisão** é qualquer escolha de projeto que o diff evidencia e que não estava determinada
pelo pedido. São exemplos de decisões: onde colocar uma nova regra de negócio, se criar uma
interface ou uma classe concreta, se reusar código existente ou duplicar, se atualizar o
`ARCHITECTURE.md`. Não é decisão: usar o nome de classe fornecido pelo pedido, criar o endpoint
exatamente como o pedido especifica, aplicar a migration SQL pedida.

**Unidade de codificação:** um commit (um passo de uma cadeia). Codifique o diff completo do
commit — não só os arquivos mais alterados.

---

## Instrução para avaliadores

Leia o diff completo do commit gerado pelo agente em cada passo. Para cada categoria abaixo,
atribua um ou mais códigos ao commit (separados por vírgula quando mais de um se aplica).
Registre dúvidas na coluna "Observação" — elas são resolvidas em reunião antes de fechar a
análise.

**Regra de ouro:** codifique o que o diff **mostra**, não o que você acha que o agente
pretendia.

**Regra de conflito:** se a mesma mudança parece se encaixar em dois códigos, registre ambos
e anote a dúvida.

---

## Categoria 1 — Localização da mudança (LOC)

**Definição:** onde o código principal do novo comportamento foi colocado. Use LOC-MUL quando
a mudança se distribui por mais de uma camada em proporções parecidas.

| Código | Definição | Exemplo | Contraexemplo |
|---|---|---|---|
| LOC-DOM | Mudança no pacote de domínio | Nova regra de negócio em `Tarefa.java` | Novo campo na entidade JPA sem lógica de negócio (→ LOC-PER) |
| LOC-APP | Mudança no pacote de aplicação (casos de uso, portas) | Novo caso de uso em `port.in` | Novo método num controlador (→ LOC-WEB) |
| LOC-WEB | Mudança no adaptador de entrada (web/HTTP) | Novo endpoint em `TarefaController` | Nova rota no HTML estático (→ LOC-FRO) |
| LOC-PER | Mudança no adaptador de saída (persistência) | Nova query no repositório JPA | Nova tabela de join sem código Java (→ LOC-INF) |
| LOC-CFG | Mudança em configuração ou composição | Novo bean em `Montagem.java` | Novo `application.properties` com chave de banco (→ LOC-INF) |
| LOC-INF | Mudança em infraestrutura (migration SQL, Docker, pom.xml) | Nova coluna em `V2__...sql` | Novo `@Entity` com `@Table` (→ LOC-PER) |
| LOC-FRO | Mudança no front-end (HTML, JS, CSS) | Novo campo em `index.html` | Novo `data-testid` em template Thymeleaf sem lógica JS (→ LOC-WEB) |
| LOC-TST | Mudança ou adição de testes pelo agente | Novo `@Test` escrito pelo agente | Teste criado pela suíte oculta (nunca aparece no diff do agente) |
| LOC-DOC | Mudança no `ARCHITECTURE.md` | Atualização da lista de pacotes | Comentário em Javadoc (→ LOC-DOM ou LOC-APP) |
| LOC-MUL | Mudança distribuída em duas ou mais camadas sem camada dominante | Nova funcionalidade com domain + app + web em proporções iguais | Um arquivo em domínio + muitos arquivos em persistência (→ LOC-PER) |

---

## Categoria 2 — Conformidade estrutural (EST-C)

**Definição:** se a mudança respeita as regras de arquitetura hexagonal declaradas no
`ARCHITECTURE.md`. Use EST-C-OK quando nenhuma violação foi introduzida; use os demais sempre
que qualquer violação aparecer no diff.

| Código | Definição | Exemplo | Contraexemplo |
|---|---|---|---|
| EST-C-OK | Nenhuma violação introduzida | Novo caso de uso com interface de porta correta | — |
| EST-C-DEP | Dependência proibida criada | `domain` importa Spring `@Service`; controlador importa `JpaRepository` | Domínio importa `java.util.List` (permitido) |
| EST-C-CIC | Ciclo de dependência introduzido | `app.service.A` depende de `app.service.B` que depende de `app.service.A` | Dependência unidirecional entre camadas (normal) |
| EST-C-INV | Inversão de dependência ausente | Nova integração externa sem criar porta em `port.out` | Uso de classe interna do mesmo pacote sem interface |

---

## Categoria 3 — Estratégia de implementação (EST-I)

**Definição:** como o agente abordou a implementação do novo comportamento.

| Código | Definição | Exemplo | Contraexemplo |
|---|---|---|---|
| EST-I-INC | Incremental: adiciona ou estende sem tocar no que já existe | Novo método na classe existente sem alterar os outros | Reescrita da classe inteira para adicionar um método (→ EST-I-REW) |
| EST-I-REF | Refatora antes ou junto da adição | Extrai método privado antes de adicionar lógica nova | Renomeia variável sem mudar comportamento como parte de um commit maior (→ pode ser EST-I-INC) |
| EST-I-REW | Reescreve trecho existente sem preservar a lógica anterior | Substitui implementação de um método existente por outra incompatível | Reescreve para melhorar sem mudar comportamento observável (→ EST-I-REF) |
| EST-I-DUP | Duplica lógica que já existe em vez de reutilizá-la | Copia código de validação de `TarefaService` para `HistoricoService` | Reusar via injeção de dependência (→ EST-I-INC) |
| EST-I-ABR | Cria nova abstração (interface, classe base, utilitário genérico) | Cria `Auditavel` interface e faz `Tarefa` implementar | Cria nova implementação de interface já existente (→ EST-I-INC) |

---

## Categoria 4 — Gestão de testes (TST)

**Definição:** o que o agente fez com os testes. Essa categoria é relevante porque o agente
não pode ver a suíte oculta — só seus próprios testes (se escrever algum).

| Código | Definição | Exemplo | Contraexemplo |
|---|---|---|---|
| TST-NEN | O agente não criou nem modificou nenhum teste | Commit sem nenhum arquivo `*Test*` | Arquivo de teste presente no diff (→ outro código) |
| TST-ACE | O agente escreveu testes de aceitação do próprio pedido | `TarefaControllerTest` com cenário do pedido atual | Teste que cobre comportamento de pedido anterior (→ TST-REG) |
| TST-REG | O agente escreveu ou modificou testes que cobrem comportamento anterior | Modifica `TarefaTest` para cobrir caso existente | Adiciona teste só para o novo pedido (→ TST-ACE) |
| TST-DEL | O agente deletou ou removeu testes existentes | Remove `@Test` de método existente | Comenta linha de asserção temporariamente e restaura |
| TST-FLK | O agente adicionou `@Disabled`, `@Ignore` ou equivalente | `@Disabled("Revisitar depois")` em teste existente | Adiciona `@Tag` sem desabilitar (não é TST-FLK) |

---

## Categoria 5 — Conformidade documental (DOC)

**Definição:** se o `ARCHITECTURE.md` reflete o estado do código após o commit.

| Código | Definição | Exemplo | Contraexemplo |
|---|---|---|---|
| DOC-OK | `ARCHITECTURE.md` reflete o estado do código após o commit | Novo pacote `auditoria` criado e documentado | — |
| DOC-LAG | Módulo ou regra nova no código não está no `ARCHITECTURE.md` | Pacote `notificacao` criado sem entrar no `ARCHITECTURE.md` | Classe privada interna sem impacto arquitetural |
| DOC-INV | `ARCHITECTURE.md` descreve algo que o código não implementa mais | Remove pacote `evento` mas mantém no documento | — |
| DOC-NOP | `ARCHITECTURE.md` não foi tocado neste commit | — | — |

> DOC-NOP é neutro e deve sempre ser combinado com DOC-OK (nenhuma mudança arquitetural no
> commit) ou DOC-LAG (mudança arquitetural mas sem atualização do documento).

---

## Protocolo de calibração

1. Antes de codificar os dados da coleta completa, os dois avaliadores codificam
   independentemente a mesma amostra aleatória de **20% dos commits** (semente fixa: 7).
2. Calculam o kappa de Cohen por categoria.
3. Categorias com kappa < 0,60: revisão conjunta das discordâncias, ajuste das definições ou
   exemplos se necessário. Uma segunda rodada de calibração com novos exemplos é feita.
4. O resultado da calibração (kappa por categoria, tabela de discordâncias e resolução) é
   registrado em `docs/s02/codificacao-decisoes.md`.
5. Só após kappa ≥ 0,60 em todas as categorias a codificação completa começa.

---

## Regra de resolução de discordâncias na codificação completa

Discordâncias são resolvidas por consenso entre os dois avaliadores. Se não houver consenso
em até 10 minutos de discussão, o terceiro membro (papel C) desempata.
