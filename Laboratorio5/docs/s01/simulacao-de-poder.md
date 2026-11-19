# Simulação de poder (S01)

Base: PLANEJAMENTO.pdf, seção 3.9 ("simulação de poder reaproveitando o Lab04, para definir o número de cadeias") e 4.1 (10 a 15 cadeias por modo, número final pela simulação). Código: `analysis/power.py`. Resultados: `results/power/`.

> **Estes números são provisórios.** Os parâmetros do processo gerador são **suposições** de trabalho, não medidas. Assim que o piloto existir, rode `python -m analysis.power --piloto data/pilot/passos.csv` para trocar as suposições por estimativas do piloto e atualize este documento.

## O que foi reaproveitado do Lab04

O desenho é o do Lab04: Monte Carlo com `numpy.random.default_rng(42)`, `repetições` por ponto da grade, poder = proporção de `p < 0,05` de cada teste, margem de erro de 95% pela aproximação normal da proporção, e **calibração pelo erro tipo I** (efeito zero deve dar perto de 5%). O gerador lognormal do Lab04 foi trocado por um processo gerador de regressão por cadeia, porque o desfecho agora é uma contagem de testes que falham em cadeias de 10 passos.

## Processo gerador (suposições)

Para cada cadeia e passo, a probabilidade de um teste de regressão falhar é `expit(logit(p_base) + u_cadeia + (b_regen + b_extra · incremental) · passo + b_tensiona · tensiona)`, e `reg_failed ~ Binomial(reg_total, p)`.

| Parâmetro | Valor | Significado |
|---|---|---|
| `p_base` | 0,5% | taxa de regressão no passo 0, modo regenerado |
| `sd_cadeia` | 0,5 (logit) | desvio-padrão do efeito aleatório da cadeia |
| `b_regen` | 0,03 por passo | inclinação da linha de base (regenerado) |
| `b_extra` | 0,05 / 0,10 / 0,20 por passo | degradação extra do incremental: cenários pequeno, médio, grande |
| `b_tensiona` | 0,5 | efeito de um pedido que tensiona a arquitetura |
| `reg_total` | 40 + 6 × passo | a suíte de regressão cresce com os pedidos aceitos |

As cadeias do incremental e do regenerado são **independentes** por padrão (`cadeia_compartilhada = False`). Quando o efeito da cadeia é compartilhado entre os modos, Welch e Mann-Whitney ficam conservadores (erro tipo I ≈ 0 em teste preliminar) e só o teste pareado é adequado; isso depende da resposta do papel B sobre o pareamento (ver `plano-de-analise.md`, seção 3).

## Testes comparados

Cada cadeia vira um número: a **taxa média de regressão nos passos 1 a 10**. Com k cadeias por modo, comparam-se (bicaudal, α = 0,05):

- **Welch** e **Mann-Whitney** (cadeias independentes), os dois testes do Lab04;
- **Wilcoxon pareado** por `chain_id`;
- **log-rank** do passo da primeira regressão.

Esse resumo por cadeia é mais pobre que o GLMM final (que usa os dados por passo), então os números abaixo são **conservadores** para o teste principal de H4.

## Resultado (2.000 repetições por ponto, semente 42)

Margem de erro de 95% de qualquer célula: no máximo ±0,022.

**Calibração (efeito zero, k = 10):** Welch 0,044; Mann-Whitney 0,043; Wilcoxon pareado 0,048; log-rank 0,066. Os três primeiros ficam perto de 5%. O log-rank fica um pouco acima (discreto, poucos eventos distintos), o que reforça mantê-lo como teste secundário.

**Poder do Welch (primário) por cadeias por modo:**

| Cenário (b_extra) | 3 | 5 | 8 | 10 | 12 | 15 | 20 |
|---|---|---|---|---|---|---|---|
| pequeno (0,05) | 0,04 | 0,08 | 0,12 | 0,16 | 0,19 | 0,23 | 0,29 |
| médio (0,10) | 0,10 | 0,22 | 0,41 | 0,56 | 0,64 | 0,76 | 0,87 |
| grande (0,20) | 0,30 | 0,69 | 0,96 | 1,00 | 1,00 | 1,00 | 1,00 |

Mann-Whitney acompanha o Welch (cenário médio, k = 20: 0,87). O Wilcoxon pareado fica ligeiramente abaixo e, com k = 3 ou 5, é **incapaz de rejeitar** por construção: o menor p exato bicaudal é 0,25 (k = 3) e 0,0625 (k = 5). O log-rank tem poder baixo em qualquer cenário (cenário grande, k = 20: 0,25; médio: 0,12), porque com ~46 a 100 testes por passo quase toda cadeia regride nos dois modos e o passo da primeira regressão discrimina pouco.

## Leitura e recomendação provisória

1. **Se o efeito do incremental for grande (b_extra ≈ 0,20), 8 cadeias por modo bastam** (poder ≈ 0,96).
2. **Se for médio (≈ 0,10), são necessárias cerca de 20 cadeias por modo** para 80% de poder neste resumo conservador (15 dão 0,76). Isso passa dos 10 a 15 previstos no planejamento e é o principal ponto a levar à decisão do piloto.
3. **Efeito pequeno não é detectável com 20 cadeias** (poder 0,29) por este teste; ficaria só o GLMM por passo, que tem mais informação, mas cujo poder não foi simulado nesta versão.
4. **Custo:** 2 modos × k cadeias × 10 passos; k = 15 são 300 execuções do Claude Code e k = 20 são 400. A estimativa de custo real vem do piloto (`custo_usd` por cadeia).

Decisão provisória: planejar **15 cadeias por modo** (o teto do planejamento) e usar o piloto para ver se o efeito observado justifica subir para 20 ou permite descer para 10. **Não é uma decisão do grupo ainda.**

## Limitações da simulação

- O GLMM por passo não foi simulado (custoso e dependente de estimativas do piloto); o resumo por cadeia é um limite inferior de poder para H4.
- Os parâmetros são suposições. Em particular, `p_base` e `reg_total` definem quanto "ruído de contagem" existe; num piloto sintético de 3 cadeias com `p_base` de 2% e 40+ testes, o critério de teto falhou (todas as cadeias do regenerado regrediram até o passo 2), o que é uma pista do que o piloto precisa verificar (critério "sem piso nem teto").
- H2, H3 e H5 não entram nesta simulação (só a regressão, o desfecho primário).

## Como reproduzir

```bash
python -m analysis.power --repeticoes 2000        # grade completa, escreve results/power/
python -m analysis.power --piloto data/pilot/passos.csv   # parâmetros estimados do piloto
```

Arquivos: `poder.csv` (cenário × cadeias × teste), `erro_tipo_i.csv`, `parametros.txt` (parâmetros usados).
