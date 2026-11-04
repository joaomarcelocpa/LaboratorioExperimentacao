# Cenário: t de Welch × Mann-Whitney — tempo até o merge de PRs

## Pergunta

PRs de agentes de IA que recebem revisão de bot demoram um tempo diferente até o merge em comparação com PRs revisados só por humanos?

## Hipóteses

- **H₀:** As distribuições de `horas_ate_merge` dos grupos `com_bot` e `sem_bot` são iguais — o bot de revisão não altera o tempo até o merge.
- **H₁:** As distribuições de `horas_ate_merge` diferem entre os grupos — o bot de revisão está associado a um tempo de merge diferente.

## Tipo de teste: bicaudal

O teste é **bicaudal**. Não há razão prévia para apostar em uma direção: o bot pode acelerar o merge (feedback automatizado chega mais rápido e o autor resolve os comentários em menos tempo) ou atrasar (o bot abre mais rodadas de revisão, gerando mais ciclos antes do merge). Como queremos detectar diferença em qualquer sentido, a hipótese alternativa é bilateral.

## Parâmetros da simulação

Os dados reais são fortemente assimétricos: a maioria dos PRs é mesclada em poucas horas, mas alguns poucos demoram dias ou semanas, puxando a média para cima. Essa assimetria de cauda longa é característica de uma distribuição **lognormal**, por isso usamos `numpy.random.default_rng(42).lognormal(mean=μ, sigma=σ, size=n)`.

Os parâmetros μ e σ são a média e o desvio-padrão do **logaritmo natural** das horas, calculados diretamente dos dados reais:

| Grupo    | n  | Mediana real (h) | Média real (h) | μ (log) | σ (log) |
|----------|----|-----------------|---------------|---------|---------|
| com_bot  | 30 |  7,26           | 43,98         | 1,616   | 2,374   |
| sem_bot  | 30 | 17,84           | 132,02        | 2,638   | 2,671   |

A mediana simulada será `exp(μ)`: ≈ 5,0 h (com_bot) e ≈ 14,0 h (sem_bot), próximos dos valores reais.

## Hipótese do grupo (antes de simular)

Esperamos que o **Mann-Whitney** se saia melhor neste cenário.

O t de Welch compara **médias**. Com n=30 e dados lognormais cheios de outliers (PRs que demoram centenas de horas), a média amostral é muito instável — um único PR extremo pode movê-la consideravelmente. Isso prejudica tanto o controle do erro tipo I quanto o poder do teste.

O Mann-Whitney compara **postos** (a ordem relativa dos valores). Por não depender dos valores absolutos, é naturalmente robusto a outliers e à assimetria da lognormal. Esperamos que ele mantenha o erro tipo I próximo de 5% e detecte o efeito com maior poder quando a diferença de localização for moderada.

A vantagem do t de Welch só apareceria se os dados fossem próximos de uma normal — o que claramente não é o caso aqui (σ_log ≈ 2,4–2,7 indica distribuição muito dispersa em escala logarítmica).
