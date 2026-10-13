# Lab 3 — Sprint 1 em linguagem simples (arquivo temporário)

## A ideia em uma frase
Pegamos os repositórios populares do GitHub, ficamos com 100 que usam CI e lançam releases com frequência, baixamos os dados deles e calculamos 4 métricas (DORA): **frequência de deploy, lead time, taxa de falha e tempo de recuperação**.

---

## Passo a passo (em ordem)

### Passo 1 — Montar a lista de candidatos (João)
- Busca no GitHub por faixa de estrelas (1k–2k, 2k–5k, 5k–10k, 10k–50k, 50k+).
- O GitHub só devolve 1.000 resultados por busca. Se uma faixa enche, o código divide a faixa ao meio e busca de novo.
- Já nesse passo saem: duplicados (26), arquivados (5.361) e **quem não teve push desde o início da janela (22.710, corte do Miguel)**.
- Resultado: **37.353 candidatos** (`candidatos.csv`). Sem nenhum filtro de CI/releases ainda.

### Passo 2 — Filtro dos 3 critérios (João + Miguel)
Os 37 mil **não** passaram todos pelo filtro (custaria centenas de milhares de chamadas à API). Fizemos assim:
1. Embaralha os 37 mil com uma seed (reproduzível).
2. Examina um por vez, na ordem sorteada, e **para quando chegar em 100 aprovados**.
3. Cada um passa por 3 testes, do mais barato ao mais caro:
   - usa GitHub Actions?
   - tem ≥ 5 releases estáveis na janela?
   - tem ≥ 50 execuções de CI válidas na janela?

Resultado: foram examinados só **483**; 100 passaram, 383 caíram; os outros 36.870 ficaram "não examinados" (a amostra fechou antes).

### Passo 3 — Funil e descartes (João)
Sim, é só **registrar** o que aconteceu:
- `funil.csv`: em cada etapa, quantos entraram, quantos saíram e por quê (a conta tem que fechar).
- `descartes.csv`: cada repositório descartado, com a etapa e o motivo.

### Passo 4 — Coletar os dados dos 100 aprovados
**Aqui cada um baixou a sua parte.** Você não baixou tudo, nem os outros baixaram "o seu". Foi uma divisão por tema:

| Quem | O que baixa | Arquivo |
|---|---|---|
| **João** | metadados do repo (estrelas, linguagem, idade, contribuidores, tipo de dono, automação de release, % Conventional Commits) | `repos.csv` |
| **João** | issues com label de bug | `issues_bug.csv` |
| **Bernardo** | releases | `releases.csv` |
| **Bernardo** | tags (com data do commit) | `tags.csv` |
| **Bernardo** | commits entre cada release e a anterior | `commits.csv` |
| **Bernardo** | deployments de produção | `deployments.csv` |
| **Miguel** | execuções de CI (só branch principal, só `push`) | `runs.csv` |
| **Miguel** | tentativas anteriores de runs (para detectar instabilidade/flaky) | `run_attempts.csv` |
| **Miguel** | infraestrutura: cache, limite da API, repetição em erro, pipeline único, Docker, CI do GitHub | — |

(As otimizações de tags e deployments via GraphQL, que reduziram muito as chamadas, foram suas.)

### Passo 5 — Calcular as métricas
Cada um calculou as métricas dos dados que coletou:

| Quem | Calcula |
|---|---|
| **João** | CFR (c) por issues; classificação DORA (nota 1–4 por métrica, classe = mediana arredondada para baixo) |
| **Bernardo** | frequência de deploy, lead time (a) por release e (b) por commit, release corretiva, CFR (b), rework rate |
| **Miguel** | CFR (a) pelo CI, flaky, episódios de falha, tempo de recuperação, série mensal |

`pipeline/montagem.py` junta tudo em **`metricas.csv`** (1 linha por repositório, 99 linhas).

### Passo 6 — Hipóteses (cada um escreve as suas)
- João: RQ 01, 06, 07 · Bernardo: RQ 02, 03b, 08a · Miguel: RQ 03a, 04, 05, 08b (**ainda falta**).

---

## Qual dado serve para qual RQ

| RQ | Pergunta | Dados usados | Quem fez |
|---|---|---|---|
| **01** | Frequência de deploy | `releases.csv` (publicadas, estáveis, na janela) ÷ 52 semanas | Bernardo |
| **02** | Tempo entre commit e deploy (lead time) | `releases.csv` + `commits.csv` (data da release − data do commit) | Bernardo |
| **03a** | Taxa de falha pelo CI | `runs.csv` + `run_attempts.csv` (falhas ÷ falhas+sucessos) | Miguel |
| **03b** | Taxa de falha por release corretiva | `releases.csv` + `commits.csv` (patch-only ou fix/hotfix/revert em até 7 dias) | Bernardo |
| **03c** (extra) | Taxa de falha por issues de bug | `issues_bug.csv` + `releases.csv` | João |
| **04** | Tempo de recuperação | `runs.csv` → episódios de falha até o próximo sucesso | Miguel |
| **05** | Frequência × falha (Spearman) | só cruza resultados das RQ 01 e 03; não coleta nada novo | Sprint 3 |
| **06** | Que características explicam desempenho melhor | `repos.csv` (linguagem, estrelas, contribuidores, idade, automação, conventional commits) × métricas | João (coleta dos fatores) |
| **07** | Sensibilidade à definição | tags e deployments (definições alternativas de "deploy") + todas as variantes de lead time e CFR | todos |
| **08 bônus** | Rework rate / evolução mensal | `releases.csv` corretivas; `metricas_mensais.csv` | Bernardo / Miguel |

Obs.: o **funil/descartes** não responde RQ nenhuma; serve para o artigo explicar como a amostra foi escolhida (e suas limitações).

---

## Números para ter na cabeça (rodada de 100, 08/10/2026)
- 65.450 repositórios na busca → 37.353 candidatos → 483 examinados → **100 aprovados** → **99 coletados** (o `google-cloud-node`, um monorepo, deu erro).
- 3h33 de execução, ~14 mil chamadas novas à API.
- Medianas: 0,40 releases/semana · lead time 137 h · CFR(a) 4,8% · CFR(b) 43% · recuperação 3 h.
- Classes: 12 Elite, 42 High, 38 Medium, 7 Low.
- Desconfiar: CFR(b) está provavelmente inflado (o `fix` aparece em quase toda release).

## O que ainda falta na Sprint 1
- Hipóteses das RQ 03a, 04, 05, 08b (Miguel).
- README final e conferência do `funil.csv`.
- Fechar as issues #38, #39, #43, #44 e #45 no GitHub Projects.
