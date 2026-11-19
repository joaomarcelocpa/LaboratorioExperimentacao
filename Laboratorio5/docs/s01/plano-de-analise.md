# Plano de análise (S01)

Base: PLANEJAMENTO.pdf, seções 3.5, 3.6, 3.7 e 3.9. Código: `analysis/`. Tudo roda com `python -m analysis.run --sintetico` (dados sintéticos) ou `python -m analysis.run --entrada <csv>` (piloto ou coleta), com o mesmo formato de CSV nos dois casos.

## 1. Unidade de análise e desfechos

- **Unidade:** o passo de uma cadeia (`chain_id`, `mode`, `step`), medido repetidamente de 0 a 10. O passo 0 é a semente (linha-base) e fica fora dos modelos de regressão.
- **Desfecho primário:** taxa de regressão por passo = `reg_failed / reg_total`. Um teste só conta como regressão se falha **nas duas rodadas** da suíte; teste que muda de resultado entre rodadas vai para `flaky`.
- **Desfechos secundários (explicativos, não definem deterioração):** `arch_violations`, `cycles`, `files_touched`, `modules_touched`, `dup_pct`, `max_ccn`, `loc`, `doc_drift`, tokens, turnos, duração e custo. Seguindo o aviso de Goodhart e McNamara do planejamento, não existe índice composto com pesos.
- **Evento de sobrevivência:** primeiro passo ≥ 1 com `reg_failed > 0`. Cadeia sem regressão até o fim, ou encerrada por falha de execução (`status = falha`), é **censurada** no último passo concluído com sucesso.

## 2. Hipóteses e método

| Hipótese | Pergunta | Método | Função |
|---|---|---|---|
| H1 | A proporção de testes de regressão que falham cresce com o passo? | GLMM binomial `reg_falhou ~ modo * passo`, intercepto aleatório por cadeia; odds ratio com IC | `models.glmm_regressao` |
| H4 | O incremental degrada mais que o regenerado no mesmo passo? | Termo `modo:passo` do GLMM; Kaplan-Meier e log-rank do passo da 1ª regressão; diferença incremental − regenerado por passo (Wilcoxon pareado, delta de Cliff) | `models`, `survival` |
| H2 | A localidade da mudança piora com o passo? | Modelo misto de curva de crescimento para `files_touched` (e `dup_pct`, `arch_violations`), intercepto e inclinação aleatórios por cadeia; termo `modo:passo` | `models.curva_de_crescimento` |
| H3 | As cadeias divergem mais com o passo? | Variância entre cadeias de `arch_violations` por passo e modo; correlação de Spearman variância × passo | `models.variancia_entre_cadeias` |
| H5 | Pedidos que tensionam a arquitetura produzem mais violações e regressões? | GLMM com `tensiona` (regressão) e modelo misto de `arch_violations` novas por passo (diferença para o passo anterior) | `models.efeito_tipo_de_pedido` |

Complementos do plano 3.9: o **efeito além do esperado** é a diferença incremental − regenerado no mesmo passo (o regenerado é a linha de base), e o **livro de códigos** das decisões do Claude Code (2 avaliadores, kappa de Cohen) é responsabilidade do papel A na S02, fora deste pipeline.

## 3. Detalhes dos modelos

**GLMM (H1, H4).** Os dados entram expandidos: uma linha por teste de regressão executado, com `y = 1` se falhou. Efeito aleatório: intercepto por `chain_id`. O statsmodels não tem GLMM por máxima verossimilhança; usamos `BinomialBayesMixedGLM` (aproximação variacional). Os "IC 95%" que ele dá são intervalos de credibilidade aproximados e tendem a ser estreitos, então toda análise também roda um **GEE binomial com correlação permutável** (erros robustos) como sensibilidade (`glmm_sensibilidade.csv`). Se os dois discordarem em sinal ou em significância, vale o mais conservador e a divergência vai para as ameaças à validade. Se um dia houver R no ambiente, `lme4::glmer` é a conferência externa.

**Curva de crescimento (H2, H5).** `desfecho ~ modo * passo`, inclinação aleatória por cadeia (`re_formula = ~passo`). Com poucas cadeias o ajuste pode não convergir; o código cai para intercepto aleatório e registra o que foi usado na coluna `efeitos_aleatorios`.

**Kaplan-Meier e log-rank.** Estimador de Kaplan-Meier com IC de Greenwood (log-log) e log-rank de dois grupos, implementados em `analysis/survival.py` e conferidos contra o exemplo clássico de Freireich (qui-quadrado = 16,79) nos testes. Com 10 passos e muita regressão em ambos os modos o evento pode ficar pouco discriminante: a simulação de poder mostra isso (ver `simulacao-de-poder.md`), e por isso o GLMM é o teste principal de H4 e o log-rank é secundário.

**Pareamento.** A análise pareada usa `chain_id` como par (cadeia *i* incremental × cadeia *i* regenerada, mesma ordem dos pedidos). O Wilcoxon de postos sinalizados é válido mesmo que a cadeia *i* seja só um rótulo, porque o pareamento arbitrário ainda gera um teste de nível correto. **Ponto a confirmar com o papel B:** se as cadeias do regenerado são repetições independentes, ou se compartilham algo (semente do agente, ordem) com a do incremental.

## 4. Comparações múltiplas (Holm)

A família confirmatória tem uma linha por teste: H1 (inclinação), H4 (interação e log-rank), H2 (`files_touched` e `dup_pct`), H5 (regressão e violações), H3 (tendência da variância) e o Wilcoxon pareado de cada um dos 10 passos. O Holm é aplicado a todas juntas (`models.holm`), e o relatório mostra `p` e `p_holm` lado a lado (`testes_holm.csv`). Alfa = 0,05. Tamanho de efeito acompanha todo p: odds ratio (GLMM), coeficiente (modelos mistos), delta de Cliff (pareado).

## 5. Validação dos dados antes de analisar

`analysis/schema.py::validar` roda antes de qualquer modelo e recusa o CSV se houver coluna fora do esquema ou da ordem, domínio inválido, contagem negativa, `reg_failed > reg_total`, passo repetido, cadeia não contígua, linhas depois de uma falha, ou `tool_version`/`model_id` mudando durante a coleta (desvio de protocolo). Detalhes em `esquema-de-dados.md`.

## 6. Decisões que o plano deixa para depois do piloto

- Se a interação `modo:passo` do GLMM é estimável com o número de cadeias do piloto (3 por modo é pouco: usa-se o piloto para estimar parâmetros, não para concluir).
- O número final de cadeias por modo, a partir de `simulacao-de-poder.md` re-rodada com `--piloto`.
- Tratamento de outliers e dos dados censurados na S02, registrados como desvio se mudarem o protocolo.

## 7. Suposições que viram risco

| Suposição | Risco | Como o pipeline reage |
|---|---|---|
| Os testes de uma mesma cadeia são independentes dado o efeito da cadeia | Testes do mesmo passo tendem a falhar juntos (mesma causa) e o GLMM subestima a variância | GEE de sensibilidade; reportar a divergência |
| Passo ≥ 1 sem falha de execução | Cadeias censuradas cedo reduzem o poder | Falha entra como censura no KM; passos faltantes saem dos modelos mistos |
| `flaky` perto de zero | Teste instável vira ruído no desfecho | Critério do piloto exige `flaky = 0`; qualquer valor > 0 é investigado |
