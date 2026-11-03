# Guia da Sprint 1 (Lab 04)

Leia este guia antes de começar sua Issue. Ele resume o laboratório, o que o grupo já decidiu e o que cada pessoa entrega.

## 1. O laboratório em poucas palavras

Vamos comparar **dois testes estatísticos** que respondem à mesma pergunta e descobrir qual deles acerta mais. Com dados reais não dá para saber a resposta certa, então **inventamos dados no computador** (simulação) em que nós decidimos se existe diferença ou não. Assim dá para contar quantas vezes cada teste acerta ou erra.

Dois conceitos que vão aparecer o tempo todo:
- **Erro tipo I:** o teste diz que há diferença quando não há. Com nível de 5%, o esperado é errar em cerca de 5% das vezes.
- **Poder:** o teste detecta a diferença quando ela existe. Quanto maior, melhor.

## 2. Decisões já tomadas

| Item | Decisão |
|---|---|
| Par de testes | **t de Welch** (compara médias) × **Mann-Whitney** (compara postos/ordem) |
| Pergunta | PRs de agentes de IA que recebem revisão de bot são mesclados mais rápido (ou mais devagar) do que PRs revisados só por humanos? |
| Variável | `horas_ate_merge` (abertura até merge) |
| Teste | **Bicaudal**: queremos saber se há *diferença*, em qualquer direção. O bot pode acelerar (feedback rápido) ou atrasar (mais rodadas de revisão), e não temos um motivo prévio para apostar em um sentido |
| Dados reais | `data/raw/prs.csv`: 60 PRs do dataset AIDev (30 `com_bot`, 30 `sem_bot`). Origem e limitações em `data/raw/FONTE.md` |
| Semente | `numpy.random.default_rng(42)` em todo o código |

**Colunas do `prs.csv`:** `pr_id`, `grupo` (`com_bot` ou `sem_bot`), `agente`, `repositorio`, `url`, `created_at`, `merged_at`, `horas_ate_merge`, `revisor_bot`.

## 3. Números dos dados reais (para a simulação)

Os tempos são muito assimétricos: poucos PRs demoram dias e puxam a média para cima. Por isso a simulação usa uma **lognormal**.

| Grupo | n | Mediana (h) | Média (h) | Desvio-padrão (h) | μ do log | σ do log |
|---|---|---|---|---|---|---|
| com_bot | 30 | 7,26 | 43,98 | 98,48 | 1,616 | 2,374 |
| sem_bot | 30 | 17,84 | 132,02 | 254,78 | 2,638 | 2,671 |

`μ` e `σ` são a média e o desvio-padrão do **logaritmo natural** das horas, que são os parâmetros que a lognormal do NumPy recebe: `rng.lognormal(mean=μ, sigma=σ, size=n)`. A mediana da lognormal é `exp(μ)`.

## 4. O que cada pessoa entrega

### João (A)
- **#84, dados reais:** concluída (planilha, fonte e script commitados). Fechar a Issue e mover o cartão.
- **#85, dashboard:** criar o `app.py` do Streamlit com as 7 seções da especificação, na ordem, e o link do repositório no topo. Mostrar G1 e G2 quando estiverem prontos, cada um com texto de 2 a 4 frases.

### Bernardo (B)
- **#86, cenário** (`docs/cenario.md`): escrever a pergunta em uma frase, H₀ e H₁, a justificativa do teste bicaudal e, **antes de rodar qualquer simulação**, o palpite do grupo (qual teste deve se sair melhor e por quê). Dica: pense no que acontece com a *média* quando há PRs extremos, e se o Mann-Whitney sofre com isso.
- **#87, gerador e G1** (`src/gerador.py`): função que gera os dois grupos lognormais com os parâmetros da seção 3. G1 são dois histogramas (real e simulado) lado a lado. Use escala log ou limite o eixo, porque a cauda longa esmaga o gráfico.

### Miguel (C)
- **#88, os dois testes** (`src/testes.py`): aplicar `scipy.stats.ttest_ind(a, b, equal_var=False)` e `scipy.stats.mannwhitneyu(a, b, alternative="two-sided")` a **um** conjunto simulado e explicar em `docs/interpretacao_s01.md` a estatística, o p-valor e o tamanho do efeito, e se os testes concordam. Pode usar o gerador do Bernardo; até ele ficar pronto, use `rng.lognormal` com os parâmetros da seção 3.
- **#89, G2:** desenhar a distribuição da estatística do t de Welch sob H₀, com a região de rejeição sombreada nas duas caudas (teste bicaudal) e o p-valor de um exemplo marcado como área.

## 5. Ordem sugerida

1. Bernardo começa por #86 e #87. Miguel começa pela #88 com dados fictícios.
2. Miguel faz a #89 depois da #88.
3. João monta o esqueleto da #85 em paralelo e encaixa G1 e G2 no fim.

## 6. Regras

- **Todo commit cita o número da Issue**, por exemplo `Gerador lognormal (#87)`. Commits sem referência não contam na correção.
- Cada integrante é Assignee de ao menos uma Issue com código commitado.
- Mantenha o cartão no Kanban atualizado (To Do, In Progress, Done) e não deixe várias tarefas em andamento ao mesmo tempo.
- Gráficos: título, eixos com nome e unidade, legenda, e **a mesma cor para cada teste** em todos eles.
- O ambiente: `python -m venv .venv`, `source .venv/bin/activate` e `pip install -r requirements.txt`.
