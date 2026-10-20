# RQ 07 — Sensibilidade da classificação DORA à definição operacional

Rascunho da discussão da Issue #76, para o grupo revisar e levar à seção de
Resultados e Discussão (#79). Os números vêm de `python -m analise.rq07` (ou
`make reproduce`) sobre o `metricas.csv` dos 299 repositórios coletados; as
tabelas estão em `analise/saida/tabelas/rq07_*.csv` e a figura em
`analise/saida/figuras/rq07_classes_por_combinacao.png`.

## O que foi comparado

Cada repositório foi classificado (Elite, High, Medium ou Low) sob três
combinações de definições, com os mesmos cortes e a mesma regra da mediana da
C1:

| Combinação | Unidade de deploy | Lead time | CFR |
|---|---|---|---|
| C1 (referência) | release | (a) por release | (a) falha de CI |
| C2 | release + pré-release | (b) por commit | (b) release corretiva |
| C3 | tag | (b) por commit | (a) falha de CI |

O tempo de recuperação é o mesmo nas três (`recuperacao_h`). Em 26 dos 299
repositórios não há episódio de falha de CI, e eles são classificados só pelas
três notas restantes, igualmente nas três combinações. A C1 reproduz a
`classe_dora` do `metricas.csv` em todos os repositórios.

## Resultado

| Classe | C1 | C2 | C3 |
|---|---|---|---|
| Elite | 29 | 4 | 37 |
| High | 122 | 87 | 137 |
| Medium | 123 | 171 | 108 |
| Low | 25 | 37 | 17 |

| Par | n | Mudaram de categoria | Subiram | Desceram | Kappa ponderado | Leitura |
|---|---|---|---|---|---|---|
| C1 × C2 | 299 | 137 (45,8%) | 32 | 105 | 0,316 | razoável |
| C1 × C3 | 299 | 82 (27,4%) | 59 | 23 | 0,656 | substancial |
| C2 × C3 | 299 | 127 (42,5%) | 121 | 6 | 0,405 | moderada |

"Subiram" e "desceram" são do segundo membro do par em relação ao primeiro. O
kappa é o de Cohen com ponderação linear sobre as notas 1 a 4, e a leitura segue
as faixas de Landis e Koch.

**Onde a definição pesa.** Entre as notas de cada métrica, a que mais muda é o
CFR: 78,6% dos repositórios mudam de nota ao trocar o CFR (a) pelo (b), contra
47,8% ao trocar o lead time (a) pelo (b) e 7,4% a 18,7% ao trocar a unidade de
deploy (release, release + pré-release, tag). É por isso que C1 × C3, que
mantêm o mesmo CFR, concordam muito mais (kappa 0,656) que qualquer par que
envolva a C2.

## As conclusões das RQ 01 a 06 são robustas?

- **RQ 01 (frequência): robusta no nível da mediana.** A mediana é de 0,33
  releases por semana, 0,38 contando pré-releases e 0,44 contando tags. Os três
  valores caem na mesma faixa (Medium, entre 1 por mês e 1 por semana). A
  nota individual de frequência muda para 7% a 19% dos repositórios.
- **RQ 02 (lead time): robusta na mediana, frágil por repositório.** A mediana é
  de 8,3 dias por release e de 8,1 por commit, as duas na faixa Medium. Mas essas
  medianas estão pouco acima do corte de 1 semana, e 47,8% dos repositórios
  mudam de nota entre as variantes.
- **RQ 03 (CFR): não é robusta.** A mediana é de 5,2% pelo CI (faixa Elite) e de
  37,5% pela release corretiva (faixa Medium). A definição decide a conclusão.
  Pela validação manual (`docs/metodologia_b.md`), a heurística do CFR (b) tem
  precisão de 0,475 e F1 de 0,638, então parte dessa distância é erro de medida
  do (b), e não só uma diferença entre conceitos.
- **RQ 04 (recuperação): não foi testada por esta análise.** As três
  combinações usam a mesma `recuperacao_h`, porque o enunciado só varia unidade
  de deploy, lead time e CFR. Variantes como `recuperacao_sem_flaky_h` e
  `recuperacao_releases_h` existem no `metricas.csv`, mas ficam fora do desenho.
- **RQ 05 (frequência × CFR): não é robusta, e o sinal inverte.** Com o CFR (a),
  ρ = −0,092 (p = 0,11, n = 299, não significativo). Com o CFR (b), ρ = +0,708
  (p < 0,001). Uma hipótese, que esta análise não prova, é que o (b) seja em
  parte mecânico: quem publica com mais frequência tem mais chance de ter uma
  release seguida de outra em até 7 dias, e a heurística lê isso como falha.
- **RQ 06 (fatores): sensível ao CFR.** Para linguagem, o teste contra `cfr_a`
  dá p ajustado = 1,0 e contra `cfr_b` dá p ajustado = 0,0019. A análise de
  fatores não foi refeita sob a C2 e a C3, então só dá para afirmar que a
  conclusão muda com a variante de CFR.

## Síntese

O que sobrevive à troca de definição é o nível geral de frequência e de lead
time (ambos Medium na mediana) e a proximidade entre C1 e C3. O que não
sobrevive é tudo o que depende do CFR: a classe de metade dos repositórios, a
mediana do CFR, o sinal da correlação da RQ 05 e a significância de fatores da
RQ 06. Para o artigo, vale reportar sempre o CFR (a) e o (b) lado a lado, e
tratar o (b) com a ressalva de precisão da heurística.

## Limitações desta análise

- **A C3 não é uma definição "por tag" completa.** Ela troca a frequência por
  `freq_tag`, mas o lead time (b) continua medido sobre os commits entre
  releases, porque os commits só foram coletados por release. Um lead time por
  tag (commits entre tags) não existe no dataset.
- Foram só as três combinações do enunciado, com os cortes fixos da disciplina,
  que são arbitrários. Um corte diferente mudaria as proporções acima.
- O kappa ponderado supõe distâncias iguais entre classes vizinhas; é uma
  convenção, não uma propriedade dos dados.
- É uma análise exploratória sobre 299 repositórios. As interpretações acima
  (em especial a do ρ da RQ 05) são hipóteses para o grupo discutir, não
  resultados estabelecidos.
