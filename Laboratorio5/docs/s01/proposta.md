# Proposta da Sprint 1 — Lab05

**Repositório:** https://github.com/joaomarcelocpa/LaboratorioExperimentacao
**GitHub Projects:** https://github.com/users/joaomarcelocpa/projects/2

---

## 1. O software: Claude Code

### 1.1 É software real

O **Claude Code** é uma ferramenta agêntica de programação desenvolvida e mantida pela Anthropic.
Ela está disponível publicamente como pacote npm (`@anthropic-ai/claude-code`) e como aplicativo
de desktop, com documentação oficial, notas de versão e suporte ativo.

- **Site oficial:** https://claude.ai/code (acesso em 2026-11-18)
- **Documentação:** https://docs.anthropic.com/en/docs/claude-code (acesso em 2026-11-18)
- **Pacote npm:** https://www.npmjs.com/package/@anthropic-ai/claude-code (acesso em 2026-11-18)

O objeto de pesquisa é o **Claude Code em operação** — executado localmente pelo grupo com versão
e modelo fixados. Não é um repositório público do GitHub nem um dataset estático.

### 1.2 Está em operação

- **Versão da CLI fixada para o experimento:** `2.1.238` (instalada no ambiente do grupo)
- **Versão mais recente no npm em 2026-11-18:** `2.1.328`
- **Modelo fixado explicitamente:** `claude-sonnet-5-5`
- **Atualização automática:** desativada durante a coleta para garantir reprodutibilidade
- **Notas de versão oficiais:** https://docs.anthropic.com/en/docs/claude-code/release-notes
  (acesso em 2026-11-18; o changelog lista releases semanais desde o lançamento em 2025)

A ferramenta é mantida ativamente pela Anthropic com ciclos curtos de release (múltiplas versões
por semana no período de coleta), confirmando que está em operação contínua.

**Uso por empresas e organizações (com fonte):**
- Anthropic reportou em maio de 2025 que o Claude Code foi adotado por empresas como Coinbase,
  GitLab e Cloudflare em ambientes de produção
  (fonte: blog da Anthropic, "Claude Code: Agentic coding for everyone", 2025-05-22;
  acesso em 2026-11-18 — confirmar URL exato antes de submeter)
- O pacote npm acumula mais de 1 milhão de downloads semanais conforme o registro público do npm
  (fonte: https://www.npmjs.com/package/@anthropic-ai/claude-code, acesso em 2026-11-18;
  verificar número atual antes de submeter)

### 1.3 Alto impacto: adoção de assistentes de código

A adoção de assistentes de código é um fenômeno de alto impacto na engenharia de software:

- O **Stack Overflow Developer Survey 2024** reportou que 76% dos desenvolvedores usam ou planejam
  usar ferramentas de IA no fluxo de trabalho
  (fonte: https://survey.stackoverflow.co/2024/, acesso em 2026-11-18)
- O **GitHub Octoverse 2024** reportou que mais de 1,3 milhão de repositórios usaram GitHub Copilot
  ativamente, com crescimento de 50% ano a ano
  (fonte: https://octoverse.github.com/2024, acesso em 2026-11-18 — confirmar números antes de
  submeter)
- A Anthropic posicionou o Claude Code como ferramenta central para o paradigma de "agentic coding",
  em que o LLM não apenas sugere trechos mas executa tarefas completas de desenvolvimento
  (fonte: documentação oficial, acesso em 2026-11-18)

Estudar como a qualidade do código produzido por essa classe de ferramentas se comporta em sessões
longas é diretamente relevante para equipes que as adotam em produção.

---

## 2. Validação institucional

> **Pendente:** Confirmar com o professor Danilo Maia que:
> (a) o Claude Code é aceito como software para o Lab05, e
> (b) nenhum outro grupo o escolheu.
>
> Registrar aqui a resposta e a data assim que obtida.
> Exemplo: "Confirmado por [professor] em [data] via [canal]."

---

## 3. Pergunta de pesquisa

**Em pedidos consecutivos de comportamento, o código produzido pelo Claude Code se deteriora de
forma cumulativa, e essa deterioração é maior quando ele edita o próprio código do que quando
regenera o sistema a partir da especificação?**

### 3.1 Definição operacional de deterioração

Deterioração é a redução observável da qualidade do código ao longo de uma cadeia de pedidos
consecutivos, medida em quatro dimensões:

| Dimensão | Definição operacional | Desfecho |
|---|---|---|
| **Funcional (regressão)** | Testes de regressão que antes passavam e agora falham | Taxa de regressão acumulada por passo |
| **Estrutural** | Violações das regras ArchUnit e ciclos de dependência | Contagem de violações por passo |
| **Evolutiva (localidade)** | Arquivos e módulos tocados por pedido | Arquivos e módulos por passo |
| **Documental** | Deriva entre o ARCHITECTURE.md e o código (regras violadas, módulos não documentados) | Contagem de desvios por passo |

**Desfecho primário:** taxa de regressão acumulada por passo (proporção de testes que falharam
ao menos uma vez até o passo n, sobre o total de testes da suíte).

As demais dimensões são secundárias e explicativas: ajudam a entender *por que* a regressão ocorre,
não a definem.

### 3.2 O objeto de pesquisa

O objeto é o **Claude Code em operação** — a ferramenta executada com versão e modelo fixados no
ambiente controlado do grupo, recebendo pedidos via CLI não interativa (`claude -p`) e produzindo
código em um workspace isolado (container Docker descartável). Não é um repositório público do
GitHub nem um dataset de commits históricos.

---

## 4. Caminho escolhido: experimento controlado

O grupo adota o caminho do **experimento controlado**, rodando o software no ambiente do próprio
grupo, com a **semente como instrumento** (não como objeto):

- A semente é o sistema-alvo (stack Java 21 + Spring Boot 3 + Maven + PostgreSQL) que o Claude
  Code recebe para modificar. Ela é fixa, auditada pelo grupo e está fora do controle do agente.
- O fator principal manipulado é o **modo de execução**: incremental (o agente edita o código do
  passo anterior) × regenerado (workspace zerado a cada passo, o agente recebe todos os pedidos
  acumulados em um único prompt).
- A medida repetida é o **passo** (0 a 10), com a cadeia como efeito aleatório no modelo misto.

Essa escolha evita os confundidores de um estudo observacional (projetos com histórico, estilos e
tamanhos diferentes) e permite controlar o estado inicial e os pedidos.

---

## 5. Decisões tomadas (resumo de 3.2 do planejamento)

| Decisão | Escolha | Motivo |
|---|---|---|
| Stack | Java 21, Spring Boot 3, Maven, PostgreSQL em Docker | ArchUnit é maduro para regras de arquitetura; tipagem forte; stack conhecida do trio |
| Software estudado | Claude Code `2.1.238`, modelo `claude-sonnet-5-5`, atualização automática desativada | Versão e modelo fixos evitam mudança durante a coleta |
| Execução do agente | Modo não interativo (`claude -p`) com saída em JSON, sessão nova a cada passo, limite de turnos e tempo | O estado entre passos é o próprio repositório, como no uso real |
| Isolamento | Container descartável por execução, sem acesso à pasta de testes ocultos | Evita ajuste ao teste (Goodhart); permite medir a localidade pelo diff |
| Registro por execução | Transcript, tokens, custo, duração, turnos, `agent_ran_tests`; sem CLAUDE.md na semente | Variáveis explicativas e auditoria das decisões |
| Quem escreve a semente | O grupo, à mão; sem assistente de IA da Anthropic | Evita viés de estilo e contaminação |
| Estilo de arquitetura | Hexagonal (portas e adaptadores), documentada em `ARCHITECTURE.md` | Padrão conhecido e com regras verificáveis pelo ArchUnit |
| `ARCHITECTURE.md` | O agente pode editar, em todas as cadeias | Permite medir a deriva entre documento e código |
| Superfície dos testes | Híbrida: HTTP para os endpoints da semente; interface web mínima com data-testid | Pedidos descrevem comportamento; testes dirigem a mesma fronteira |
| Visibilidade dos testes | Todos ocultos e fora do workspace | Evita ajuste ao teste (Goodhart); `agent_ran_tests` entra como covariável |
| Modo regenerado | Workspace zerado + pedidos 1 a n acumulados em um único prompt | Remove dependência de trajetória; isola o efeito de editar o próprio código |
| Passo com falha | 1 nova tentativa sem feedback; se falhar de novo, cadeia termina (censurado) | Alimenta a análise de sobrevivência |
| Ordem dos pedidos | No piloto, ordem fixa P1–P4; na coleta completa, 2 ordens equivalentes por cadeia | Controla efeito de ordem |

---

## 6. GQM — template de Basili

| Objetivo (Basili) | Pergunta | Métrica | Entidade, atributo, escala |
|---|---|---|---|
| Analisar edições sucessivas por LLM, para avaliar a preservação de correção, do ponto de vista do desenvolvedor | O sistema para de fazer o que fazia? | Taxa de regressão por passo e acumulada | Produto, externo, razão (proporção) |
| Idem, aderência estrutural | O código se afasta da arquitetura de partida? | Violações ArchUnit e ciclos por passo | Produto, interno, razão (contagem) |
| Idem, custo de evolução | Ficou mais caro mudar? | Arquivos e módulos tocados por pedido | Processo, interno, razão (contagem) |
| Idem, consistência documental | A documentação descreve o código? | Deriva documento × código (regras violadas, módulos não documentados) | Produto, interno, razão (contagem) |
| Idem, durabilidade da cadeia | Quantos passos até a primeira regressão? | Passo da primeira regressão (censurado no último passo) | Razão, dado censurado |
| Apoio (não definem deterioração) | O que explica as mudanças? | Complexidade máxima, duplicação, LOC, tokens, turnos e duração | Produto, interno, razão |

> **Nota Goodhart/McNamara:** complexidade e LOC crescem naturalmente com funcionalidade e não são
> deterioração por si. Por isso a correção fica no centro, as métricas internas entram como
> explicação, o braço regenerado serve de linha de base e não se cria índice composto com pesos
> arbitrários.

---

## 7. Hipóteses

| # | Hipótese |
|---|---|
| H1 | A proporção de testes de regressão que falham cresce com o passo. |
| H2 | A localidade da mudança piora (mais arquivos por pedido) com o passo. |
| H3 | A variação estrutural entre cadeias do mesmo tratamento aumenta com o passo. |
| H4 | O modo incremental degrada mais que o regenerado no mesmo passo. |
| H5 | Pedidos que tensionam a arquitetura produzem mais violações e mais regressões que os que cabem nela. |

---

## 8. As 7 categorias (versão 1)

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada | Orienta o uso de assistentes de código em evolução de sistemas |
| Objetivos | Explicativa, com parte exploratória | Busca o mecanismo (incremental × regenerado); a codificação das decisões é exploratória |
| Abordagem | Quantitativa, com apoio qualitativo | Taxas, contagens e modelos; decisões codificadas com kappa |
| Procedimentos | Experimento controlado | Fatores manipulados e tratamentos atribuídos pelo grupo |
| Tempo | Longitudinal (medidas repetidas) | Mesma cadeia medida em cada passo |
| Controle | Experimental, com braço de controle | Modo regenerado como controle |
| Nível de evidência | Alto em validade interna, limitado em externa | Ambiente sintético, uma stack e um modelo |

---

## 9. Ameaças à validade (preliminares)

| Tipo | Ameaça | Mitigação |
|---|---|---|
| Conclusão | Poucas cadeias; testes instáveis | Simulação de poder; suíte rodada duas vezes |
| Interna | Efeito de ordem; versão do Claude Code ou modelo muda durante a coleta | Duas ordens equivalentes; versão e modelo fixados, atualização automática desativada, coleta em poucos dias |
| Construto | Testes medem comportamento, não qualidade; ArchUnit assume que a arquitetura de partida é boa | Auditoria manual de subamostra; correção no centro e estrutura como explicação |
| Externa | Uma stack, uma ferramenta com um modelo e configuração padrão, sistema pequeno; recursos como CLAUDE.md, subagentes e servidores MCP não testados | Não generalizar para outras ferramentas de IA; declarar como limitação principal |

---

## 10. O que é novo em relação ao Lab02

O Lab02 coletou métricas de repositórios públicos do GitHub (dados observacionais, projetos
heterogêneos, sem controle sobre o processo de desenvolvimento). O Lab05 difere em:

- **Objeto:** o Claude Code em operação, não um repositório histórico
- **Desenho:** experimento controlado com fator manipulado (modo incremental × regenerado), em vez
  de estudo de correlação
- **Variável de resposta:** taxa de regressão acumulada por passo (medida repetida na mesma cadeia),
  em vez de métricas de produto estáticas
- **Controle:** estado inicial idêntico entre cadeias (semente auditada), pedidos idênticos,
  modelo e versão fixados
- **Cadeia causal:** permite inferir se o modo de execução *causa* deterioração, não apenas se
  está correlacionado a ela

---

## 11. Inspiração: SlopCodeBench

O estudo se inspira no **SlopCodeBench** (referência a verificar no artigo antes de citar
formalmente; não foi usado material do repositório do benchmark). O benchmark avalia a tendência
de LLMs de introduzir código genérico ou de baixa qualidade ("slop") em tarefas de programação,
com foco em tarefas repetidas. A diferença principal é que o Lab05 mede deterioração *longitudinal*
dentro de uma única sessão de edição — um protocolo de cadeia de passos com estado persistente —
e não desempenho em tarefas independentes de um benchmark.

> **Atenção:** conferir o desenho experimental do artigo SlopCodeBench antes de citar.
> Garantir que a comparação seja precisa e que nenhuma conclusão do benchmark seja atribuída a este
> estudo.
