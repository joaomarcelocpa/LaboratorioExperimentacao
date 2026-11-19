# Relatório do piloto (S01)

Base: PLANEJAMENTO.pdf, seção 3.12. Issue: #109 (relatório), dependente dos dados do piloto da #105 (papel B).

> **Status: aguardando os dados do piloto.** Ainda não existe CSV do piloto (24 execuções do Claude Code: 3 cadeias × 2 modos × 4 pedidos). **Nenhum número abaixo é real:** as células estão vazias e a decisão está em aberto. Quando o CSV chegar, siga "Como preencher" e substitua este aviso.

## Como preencher (assim que B2 entregar o CSV)

```bash
python -m analysis.pilot data/pilot/passos.csv --orcamento-usd-cadeia <USD> --limite-horas-cadeia <horas>
python -m analysis.run --entrada data/pilot/passos.csv
python -m analysis.power --piloto data/pilot/passos.csv
```

O primeiro comando imprime a tabela dos 5 critérios (copie para a seção 2). O segundo gera tabelas e figuras em `results/passos/`. O terceiro atualiza a estimativa de poder. O orçamento e o limite de horas por cadeia são **decisão do grupo** (conferir preços e limites do plano no dia); sem eles o critério de custo fica `PENDENTE` e a decisão não fecha.

## 1. Dados do piloto

| Item | Valor |
|---|---|
| Versão do Claude Code (`tool_version`) | _a preencher_ |
| Modelo (`model_id`) | _a preencher_ |
| Data da coleta | _a preencher_ |
| Execuções (esperado: 24) | _a preencher_ |
| Cadeias × modos | 3 × 2 |
| Pedidos | P1 a P4, ordem fixa |
| Validação do CSV (`analysis.schema.validar`) | _a preencher: sem erros?_ |

## 2. Critérios de decisão (seção 3.12)

Cada critério com PASSA ou FALHA e o valor observado:

| Critério | Passa quando | Resultado | Valor observado |
|---|---|---|---|
| Execução do agente | > 95% das execuções sem erro nem tempo esgotado (1ª tentativa) | _a preencher_ | _a preencher_ |
| Determinismo dos testes | duas rodadas no mesmo código dão o mesmo resultado, nas duas superfícies (`flaky = 0`) | _a preencher_ | _a preencher_ |
| Sem piso nem teto | há regressões ou violações, mas as cadeias não quebram já no passo 2 | _a preencher_ | _a preencher_ |
| Variação entre cadeias | suficiente para estimar o poder estatístico | _a preencher_ | _a preencher_ |
| Custo e tempo | por cadeia, dentro do orçamento ou dos limites de uso e de tempo | _a preencher_ | _a preencher_ |

Como cada critério foi operacionalizado (`analysis/pilot.py`) — **interpretações que o grupo deve confirmar antes de usar o resultado:**

- **Execução do agente:** primeira tentativa sem erro e sem tempo esgotado (`retry = 0` e `run_ok = 1`), sobre as execuções dos passos 1 a 4. Com 24 execuções, uma falha ainda passa (95,8%) e duas reprovam (91,7%).
- **Determinismo:** nenhum passo com `flaky > 0`. A coluna `flaky` junta HTTP e interface; se a causa for só uma superfície, a investigação é no log da suíte, não no CSV.
- **Piso e teto:** *piso* = nenhuma regressão nem violação em todo o piloto; *teto* = em algum modo, todas as cadeias já regridem ou quebram até o passo 2. Qualquer um dos dois reprova o critério.
- **Variação entre cadeias:** desvio-padrão, entre cadeias, da taxa média de regressão maior que zero em algum modo. Com 3 cadeias por modo isso é um teste de "não degenerado", não uma estimativa precisa; a estimativa quantitativa do poder está na seção 3.
- **Custo e tempo:** custo e duração por passo extrapolados para 10 passos, comparados ao orçamento informado.

## 3. Estimativa de poder

_A preencher com `python -m analysis.power --piloto ...`: parâmetros estimados (taxa-base, inclinações, desvio entre cadeias) e o número de cadeias por modo para 80% de poder nos três cenários de efeito._ Resultado provisório com parâmetros supostos: ver `simulacao-de-poder.md` (cerca de 15 a 20 cadeias por modo para um efeito médio).

## 4. Observações do piloto

_A preencher: o que o transcript mostrou (agente saiu do workspace? rodou testes por conta própria? tempo esgotado?), falhas de passo e como a regra de nova tentativa se comportou, regressões e violações vistas por passo e por tipo de pedido (`cabe` × `tensiona`)._

## 5. Decisão

Opções (seção 3.12): **GO** (escrever P5 a P10 e seguir para a coleta completa), **GO com ajustes** (corrigir pedidos, testes ou semente e repetir um mini-piloto; se a interface for instável, plano B de HTTP) ou **NO-GO** (simplificar ou voltar a uma coleta curta).

O script sugere um ponto de partida por regra simples (0 falhas = GO; 3 ou mais falhas, ou falha de execução junto com a de custo = NO-GO; demais casos = GO com ajustes; `PENDENTE` impede concluir). **A decisão é do grupo e deve ser justificada com os valores da seção 2**, não com a sugestão.

| Campo | Valor |
|---|---|
| Decisão | _pendente_ |
| Justificativa baseada nos dados | _pendente_ |
| Ajustes exigidos (se houver) | _pendente_ |
| Revisor (papel B) | _pendente_ |
