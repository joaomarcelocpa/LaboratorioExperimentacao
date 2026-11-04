# Interpretação da Sprint 1: t de Welch × Mann-Whitney em um conjunto simulado

Conjunto simulado com `gerar_dados(seed=42)` (lognormal, n = 30 por grupo, parâmetros do `docs/cenario.md`). Para reproduzir: `python -m src.testes`.

Testes bicaudais, α = 0,05. H₀: o bot de revisão não altera o tempo até o merge.

## Resultados

| Grupo   | Mediana (h) | Média (h) |
|---------|-------------|-----------|
| com_bot | 6,35        | 16,27     |
| sem_bot | 22,09       | 210,07    |

| Teste | Estatística | p-valor | Decisão (α = 0,05) |
|-------|-------------|---------|--------------------|
| t de Welch (`equal_var=False`) | t = −1,361 (gl = 29,0) | 0,184 | não rejeita H₀ |
| Mann-Whitney (`two-sided`) | U = 307,0 | 0,035 | rejeita H₀ |

Tamanhos de efeito:

- **d de Cohen nas horas:** −0,35 (efeito pequeno). O sinal negativo indica que `com_bot` tem média menor.
- **d de Cohen no log das horas:** −0,64 (efeito médio). Na escala logarítmica, que é a natural para uma lognormal, a diferença é maior.
- **Probabilidade de superioridade P(com_bot > sem_bot):** 0,341, ou seja, U/(n₁·n₂) = 307/900. Em 34% dos pares sorteados, o PR com bot demora mais que o sem bot. Em 66%, o PR com bot é mesclado antes.

## Interpretação

**Estatística.** O t de Welch vale −1,36: a diferença de médias (≈ 194 h) equivale a pouco mais de uma vez e meia o erro-padrão. O valor é grande em horas, mas o erro-padrão também é, porque a média do grupo `sem_bot` é puxada por poucos PRs extremos. O U de 307 está bem abaixo do valor esperado sob H₀ (450 = 30·30/2), o que indica que os postos de `com_bot` tendem a ser menores.

**p-valor.** Com p = 0,184, o Welch não consegue distinguir a diferença de médias do acaso. Com p = 0,035, o Mann-Whitney rejeita H₀: a ordem relativa dos valores aponta que `com_bot` é mesclado antes.

**Os testes não concordam.** Os dois ficam em lados opostos de α = 0,05. Isso não é contradição, porque respondem a perguntas diferentes: o Welch pergunta se as *médias* diferem; o Mann-Whitney pergunta se um grupo tende a ter valores maiores que o outro. Em dados lognormais com σ_log ≈ 2,4–2,7, a média é dominada pela cauda: o maior valor de `sem_bot` sozinho pesa muito na média e na variância, inflando o erro-padrão e reduzindo a estatística t. O Mann-Whitney usa só os postos e não sofre com isso.

**Alinhamento com a hipótese do grupo.** O resultado vai na direção esperada em `docs/cenario.md`: o Mann-Whitney detecta o efeito com mais poder que o Welch. Ressalva importante: é **um único** conjunto simulado. Uma divergência isolada pode acontecer por sorte da amostra; quem mede a taxa de erro tipo I e o poder de cada teste é a simulação de Monte Carlo com muitas repetições, que vem nas próximas etapas.
