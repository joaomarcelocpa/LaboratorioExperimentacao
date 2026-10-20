# RQ 08b — As métricas de CI melhoraram ou pioraram ao longo da janela?

Rascunho da Issue #77, para o grupo revisar e levar à seção de Resultados e
Discussão (#79). Os números vêm de `python -m analise.rq08b` (ou
`make reproduce`) sobre o `metricas_mensais.csv`, o `releases.csv` e o
`commits.csv.gz`; as tabelas estão em `analise/saida/tabelas/rq08b_*.csv` e a
figura em `analise/saida/figuras/rq08b_serie_amostra.png`. A hipótese registrada
antes da análise está em `docs/hipoteses.md` (RQ 08b).

## O que foi feito

A Issue pede o cálculo por trimestre. Testar só por trimestre não funciona: com 4
pontos, o menor p-valor possível do Mann-Kendall, numa série perfeitamente
crescente, é cerca de 0,08 a 0,09 (0,0894 no `pymannkendall`, 0,0833 pelo teste
exato), então nenhum repositório poderia chegar a p < 0,05 por limitação do
teste e não dos dados. Por isso o desenho segue o plano da Sprint 1:

- **Teste mensal (12 pontos) para as métricas de CI:** o CFR de CI (a) e a
  mediana do tempo de recuperação, por repositório. Mês sem valor (menos de 5
  runs válidos) fica de fora, e o repositório com menos de 8 meses válidos não é
  testado.
- **Frequência e lead time por trimestre (4 pontos), só descritivo:** mediana
  entre repositórios, sem teste.
- **Teste:** `pymannkendall.original_test` com α = 0,05, queda é melhora nas duas
  métricas, e a inclinação de Sen como tamanho de efeito (p.p. por mês no CFR,
  horas por mês na recuperação). O teste de Hamed-Rao ao lado, como checagem de
  autocorrelação.
- **Correção para muitos testes:** proporções com e sem Holm, uma família por
  métrica.

## Resultado por repositório

| | CFR de CI (a) | Tempo de recuperação |
|---|---|---|
| Repositórios | 299 | 299 |
| Testados (≥ 8 meses válidos) | 211 | 94 |
| Fora do teste (< 8 meses válidos) | 88 | 205 |
| Melhora | 12 (5,7%) | 4 (4,3%) |
| Piora | 11 (5,2%) | 2 (2,1%) |
| Sem tendência | 188 (89,1%) | 88 (93,6%) |
| Melhora, com Holm | 0 | 0 |
| Piora, com Holm | 1 | 0 |

As proporções têm como denominador os testados. O teste de Hamed-Rao não mudou o
veredito de nenhum repositório. Entre os com tendência significativa, a
inclinação de Sen mediana foi de −2,0 p.p./mês nas melhoras do CFR e de +1,9
p.p./mês nas pioras; na recuperação, de −0,11 h/mês nas melhoras e +0,47 h/mês
nas pioras.

## Visão da amostra

A série mensal da mediana entre repositórios não tem tendência em nenhuma das
duas métricas: CFR de CI (a), p = 0,84; tempo de recuperação, p = 0,19. A mediana
do CFR fica entre 1,5% e 4,0% ao longo dos 12 meses, e a do tempo de recuperação
entre 2,9 e 5,4 horas.

Frequência e lead time por trimestre (descritivo, sem teste):

| Trimestre | Releases/semana (mediana) | Lead time (a), horas (mediana) |
|---|---|---|
| 2025T4 | 0,15 | 296 |
| 2026T1 | 0,31 | 259 |
| 2026T2 | 0,31 | 195 |
| 2026T3 | 0,38 | 237 |

## O que isso diz sobre a hipótese

- **"A maioria não apresenta tendência significativa": confirmada.** 89% dos
  repositórios no CFR e 94% na recuperação.
- **"Entre os com tendência, mais melhora que piora": não se sustenta.** No CFR são
  12 melhoras contra 11 pioras, um empate prático. Na recuperação são 4 contra 2,
  números pequenos demais para concluir. Com a correção de Holm não sobra nenhuma
  melhora, e sobra uma piora no CFR.
- **Quanto disso é acaso.** Com α = 0,05, esperam-se cerca de 10,6 resultados
  significativos por acaso entre os 211 testes do CFR, e foram 23; na recuperação,
  4,7 esperados e 6 observados. O excesso no CFR sugere que alguns repositórios
  tenham mesmo tendência, mas a maior parte do que aparece é compatível com ruído,
  e o Holm confirma isso.

## Limitações

- **A recuperação vale só para quem falha com frequência.** 205 dos 299
  repositórios (69%) não têm 8 meses com episódio de falha e ficam fora do teste,
  então o resultado da recuperação descreve os 94 repositórios com CI mais
  instável, e não a amostra.
- **Pouco poder estatístico.** Cada mês tem poucos runs, então o CFR mensal é
  uma proporção ruidosa, e 12 pontos dão ao teste pouca chance de detectar
  tendências moderadas. "Sem tendência" aqui significa que não foi possível
  detectar, e não que tenha ficado estável.
- **Empates.** Muitos meses têm CFR 0, e as séries com empates deixam o p-valor
  aproximado. Contra o teste exato do `scipy`, a direção coincide em 209 dos 211
  repositórios do CFR e em 94 dos 94 da recuperação; os 2 que divergem estão na
  fronteira de p = 0,05. A direção sai do sinal do teste (e não da inclinação de
  Sen, que pode ser 0 com muitos empates).
- **Ameaças já previstas no plano:** mudanças no próprio pipeline do projeto
  (workflow criado ou removido no meio da janela), sazonalidade (as férias de fim
  de ano podem explicar a frequência menor de 2025T4) e regressão à média.

Todas as interpretações acima são hipóteses para o grupo discutir, e não
resultados estabelecidos.
