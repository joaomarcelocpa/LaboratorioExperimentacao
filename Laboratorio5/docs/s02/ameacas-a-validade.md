# Ameaças à validade — versão final (S02)

Base: PLANEJAMENTO.pdf, seções 3.10 e 4.1. Issue: #116.

Evolução das ameaças preliminares da S01 (`docs/s01/proposta.md`, seção 9) para uma versão
final, com os quatro tipos, mitigação e o que de fato aconteceu na coleta.

> **Células marcadas com `_a preencher_`** dependem dos dados da coleta completa (taxas de
> erro, flaky e censura) e do relatório de análise. Preencher após a coleta e a auditoria
> (`docs/s02/auditoria-manual.md`) estiverem completos.

---

## 1. Ameaças à validade de conclusão

Dizem respeito à relação entre os dados e as conclusões estatísticas — erro do Tipo I e II,
poder e replicabilidade.

### 1.1 Número de cadeias e poder estatístico

**Ameaça:** o número de cadeias por modo pode ser insuficiente para detectar efeitos pequenos
com o poder desejado de 80%. Com poucas cadeias, o estudo tem poder para detectar apenas
efeitos grandes.

**Mitigação:** simulação de poder a priori (`results/power/poder.csv`) com estimativa dos
parâmetros do piloto. O número de cadeias da coleta completa foi determinado pela simulação
(veja `docs/s01/simulacao-de-poder.md`).

**O que aconteceu na coleta:**
- Número de cadeias coletadas: `_a preencher_`
- Poder estimado a posteriori: `_a preencher_`

---

### 1.2 Testes instáveis (flaky)

**Ameaça:** um teste que oscila entre passada e falha em rodadas consecutivas do mesmo código
(flaky) contamina a medição de regressão — pode gerar falsos positivos ou negativos em qualquer
passo.

**Mitigação:** a suíte é rodada duas vezes no mesmo código por passo. Um passo é marcado como
`flaky=1` quando os dois resultados divergem; esses passos são excluídos do cômputo de
regressão naquele passo mas entram na análise de sobrevivência.

**O que aconteceu na coleta:**
- Taxa de passos com `flaky=1`: `_a preencher_` (esperado < 5%)
- Passos excluídos por flaky: `_a preencher_`

---

### 1.3 Poucos dados por modo em passos avançados

**Ameaça:** cadeias censuradas reduzem o tamanho efetivo da amostra nos passos finais, o que
pode inflar a variância e comprometer as conclusões sobre o comportamento tardio.

**Mitigação:** análise de sobrevivência (Kaplan-Meier + log-rank) para os dados de censura;
análise de regressão por passo usa apenas cadeias não censuradas até o passo em questão.

**O que aconteceu na coleta:**
- Taxa de censura por modo: incremental `_a preencher_`, regenerado `_a preencher_`
- Passo médio de censura: `_a preencher_`

---

## 2. Ameaças à validade interna

Dizem respeito a confundidores que podem explicar o resultado sem ser o tratamento.

### 2.1 Efeito de ordem dos pedidos

**Ameaça:** a posição de um pedido na sequência pode influenciar o resultado independentemente
do seu conteúdo. Pedidos em posições posteriores têm mais contexto acumulado (modo incremental)
ou prompt maior (modo regenerado), o que pode facilitar ou dificultar a implementação.

**Mitigação:** duas ordens equivalentes (Ordem A e Ordem B, definidas no protocolo congelado),
com metade das cadeias em cada ordem por modo. A ordem é uma covariável na análise.

**O que aconteceu na coleta:**
- Distribuição de cadeias por ordem: `_a preencher_`
- Efeito de ordem observado na análise: `_a preencher_`

---

### 2.2 Mudança de versão ou modelo durante a coleta

**Ameaça:** se a versão do Claude Code ou o modelo subjacente mudar entre cadeias, cadeias
coletadas em datas diferentes não são comparáveis.

**Mitigação:** versão `2.1.323` fixada com atualização automática desativada; modelo
`claude-sonnet-5-5` fixado no comando de cada execução. Versão e modelo são registrados em
cada execução no transcript.

**O que aconteceu na coleta:**
- Versão usada em todas as cadeias: `_a preencher — confirmar no transcript_`
- Alguma mudança detectada: `_a preencher_`

---

### 2.3 Falhas de passo e dados censurados

**Ameaça:** cadeias que terminam cedo por falha do agente não são uma amostra aleatória —
podem ser sistematicamente as cadeias em que o agente estava "se perdendo", o que introduz
viés de sobrevivência nos passos avançados.

**Mitigação:** a regra de passo falho (1 nova tentativa sem feedback; falha dupla censura a
cadeia) é aplicada uniformemente. Cadeias censuradas são analisadas separadamente na análise
de sobrevivência. O índice de censura é reportado como covariável.

**O que aconteceu na coleta:**
- Número de cadeias censuradas por falha: `_a preencher_`
- Passo típico de censura: `_a preencher_`
- Desvios registrados em `docs/s02/desvios.md`: `_a preencher_`

---

## 3. Ameaças à validade de construto

Dizem respeito a se as métricas medem o que se pretende medir.

### 3.1 Testes medem comportamento, não qualidade interna

**Ameaça:** os testes verificam se o sistema faz o que os pedidos pedem, não se o código está
bem estruturado. Um agente pode passar em todos os testes e ainda assim produzir código difícil
de manter ou estender.

**Mitigação:** a deterioração estrutural é capturada separadamente pelo ArchUnit (violações) e
pela codificação das decisões (livro de códigos). A correção funcional é o desfecho primário;
a estrutura entra como covariável ou desfecho secundário.

**O que aconteceu na coleta:**
- Correlação entre violações ArchUnit e taxa de regressão: `_a preencher_`

---

### 3.2 ArchUnit assume que a arquitetura de partida é boa

**Ameaça:** as regras do ArchUnit verificam conformidade com o `ARCHITECTURE.md` da semente.
Se a semente já tiver decisões ruins, o ArchUnit não as detecta — só detecta desvios do
padrão estabelecido, bom ou ruim.

**Mitigação:** a semente foi construída manualmente pelo grupo com revisão explícita da
arquitetura (`docs/s01/revisao-da-semente.md`). O resultado da revisão é registrado abaixo.

**Resultado da revisão da semente:**
- Violações encontradas na semente: `_a preencher — ver revisao-da-semente.md_`
- Avaliação geral da qualidade arquitetural da semente: `_a preencher_`

---

### 3.3 Resultado da auditoria manual

**Ameaça:** falsos negativos das métricas automáticas (problemas que o agente introduziu mas
que os testes e o ArchUnit não pegaram) subestimam a deterioração real.

**Mitigação:** auditoria manual de ~20 saídas como padrão-ouro (ver `docs/s02/auditoria-manual.md`),
com comparação entre veredito manual e métricas automáticas.

**O que aconteceu na auditoria:**
- Taxa de falsos negativos de regressão: `_a preencher_`
- Taxa de falsos negativos de violação arquitetural: `_a preencher_`
- Taxa de falsos positivos: `_a preencher_`
- Interpretação: `_a preencher_`

---

## 4. Ameaças à validade externa

Dizem respeito à generalização dos resultados para outros contextos.

### 4.1 Uma única stack tecnológica

**Ameaça:** o experimento usa Java 21, Spring Boot 3, Maven e PostgreSQL. Os resultados podem
não se generalizar para outras linguagens (Python, TypeScript), frameworks ou paradigmas
(funcional, orientado a eventos).

**Mitigação:** não aplicável — a restrição é parte do desenho. Declarar como limitação
principal: **os resultados descrevem o comportamento do Claude Code na stack usada e não devem
ser generalizados para outras stacks sem replicação.**

---

### 4.2 Um único modelo de linguagem e uma configuração padrão

**Ameaça:** o experimento usa exclusivamente `claude-sonnet-5-5` em modo padrão (sem
CLAUDE.md, subagentes ou servidores MCP). Resultados podem diferir para outros modelos
(GPT-4o, Gemini, Llama), outros modos do Claude Code ou versões futuras do mesmo modelo.

**Mitigação:** não aplicável — a restrição é parte do desenho. Declarar como limitação:
**os resultados descrevem o comportamento de uma versão específica do Claude Code com
configuração padrão e não devem ser generalizados para outras ferramentas de IA.**

---

### 4.3 Sistema sintético e pequeno

**Ameaça:** a semente é um sistema simples de gerenciamento de tarefas, desenvolvido
especialmente para o estudo. Sistemas reais são maiores, têm mais dívida técnica, histórico de
contribuidores múltiplos e requisitos de negócio mais complexos.

**Mitigação:** o sistema pequeno é uma escolha deliberada para controlar o estado inicial e
tornar a coleta viável. Declarar como limitação: **os resultados descrevem a deterioração num
sistema pequeno e controlado; sistemas maiores podem apresentar padrões distintos.**

---

### 4.4 Sem CLAUDE.md, subagentes ou MCP

**Ameaça:** usuários avançados do Claude Code podem configurar CLAUDE.md, usar subagentes
ou adicionar servidores MCP para guiar o agente. O experimento usa a configuração padrão,
sem nenhum desses recursos, o que pode subestimar o desempenho em uso real.

**Mitigação:** a configuração padrão foi escolhida para medir o comportamento de base do
agente sem otimizações. Declarar como limitação e sugerir como trabalho futuro: **testar se
CLAUDE.md ou subagentes reduzem a deterioração.**

---

## 5. Resumo das ameaças

| Tipo | Ameaça | Mitigação | Residual |
|---|---|---|---|
| Conclusão | Poucas cadeias | Simulação de poder a priori | Poder limitado para efeitos pequenos |
| Conclusão | Testes instáveis (flaky) | Suíte rodada duas vezes; passos flaky excluídos | Taxa de flaky `_a preencher_` |
| Conclusão | Poucos dados em passos avançados (censura) | Análise de sobrevivência | Taxa de censura `_a preencher_` |
| Interna | Efeito de ordem | Duas ordens equivalentes | Efeito residual nas ordens |
| Interna | Mudança de versão/modelo | Versão e modelo fixados | Nenhuma — se confirmado na coleta |
| Interna | Falhas e censura sistêmicas | Regra uniforme + análise de sobrevivência | Viés de sobrevivência nos passos avançados |
| Construto | Testes medem comportamento, não qualidade | ArchUnit + codificação qualitativa | Qualidade interna não coberta por testes |
| Construto | ArchUnit assume semente boa | Revisão da semente documentada | Qualidade da semente como pré-condição |
| Construto | Métricas automáticas com falsos negativos | Auditoria manual de 20 saídas | FN residual: `_a preencher_` |
| Externa | Uma stack | Declarar como limitação | Alta — não generalizar para outras stacks |
| Externa | Um modelo e configuração padrão | Declarar como limitação | Alta — não generalizar para outras ferramentas |
| Externa | Sistema sintético e pequeno | Declarar como limitação | Média — sistemas reais podem diferir |
| Externa | Sem CLAUDE.md/subagentes/MCP | Declarar como limitação | Média — uso avançado pode diferir |
