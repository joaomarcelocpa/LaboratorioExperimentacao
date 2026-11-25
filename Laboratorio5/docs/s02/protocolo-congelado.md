# Protocolo congelado — coleta completa (S02)

Base: PLANEJAMENTO.pdf, seções 3.2, 3.4 e 4.1.

> **Status:** aguardando decisão GO do relatório do piloto (issue #109).
> As seções com `_a preencher_` dependem dessa decisão e dos pedidos finais P5-P10.
> Este documento deve ser congelado (tag `protocolo-v1`) **antes da primeira execução
> da coleta completa**. Qualquer mudança após a tag é um desvio — registrar em `desvios.md`.

---

## 1. Versão e modelo fixos

| Item | Valor |
|---|---|
| Versão do Claude Code | `2.1.323` (atualização automática desativada) |
| Modelo | `claude-sonnet-5-5` |
| Modo de execução | `claude -p`, saída em JSON, sessão nova a cada passo |
| Limite de turnos por passo | `_a preencher — decisão do grupo antes da coleta_` |
| Limite de tempo por passo | `_a preencher — decisão do grupo antes da coleta_` |

---

## 2. Pedidos finais (P1 a P10)

| Pedido | Título | Tipo | Arquivo |
|---|---|---|---|
| P1 | Avisos de vencimento | Cabe na arquitetura | `docs/s01/pedidos/P1.md` |
| P2 | Filtro e ordenação com 50k tarefas | Cabe na arquitetura | `docs/s01/pedidos/P2.md` |
| P3 | Isolamento de dados por empresa | Tensiona a arquitetura | `docs/s01/pedidos/P3.md` |
| P4 | Importação de tarefas via CSV | Cabe na arquitetura | `docs/s01/pedidos/P4.md` |
| P5 | Histórico de alterações | Tensiona a arquitetura | `docs/s02/pedidos/P5.md` |
| P6 | Permissões por papel | Tensiona a arquitetura | `docs/s02/pedidos/P6.md` |
| P7 | Reenvio sem duplicar (idempotência) | Cabe na arquitetura | `docs/s02/pedidos/P7.md` |
| P8 | Relatório agregado de tarefas | Cabe na arquitetura | `docs/s02/pedidos/P8.md` |
| P9 | Sincronização com serviço externo instável | Tensiona a arquitetura | `docs/s02/pedidos/P9.md` |
| P10 | Troca do banco de dados (sonda final) | Tensiona a arquitetura | `docs/s02/pedidos/P10.md` |

**Balanço de tipos:** 5 "cabe na arquitetura" (P1, P2, P4, P7, P8) e 5 "tensiona a arquitetura" (P3, P5, P6, P9, P10).

> As versões congeladas dos pedidos são os arquivos acima no commit que receber a tag `protocolo-v1`.
> Qualquer edição posterior a um pedido já é um desvio e os dados afetados devem ser
> descartados ou analisados separadamente.

---

## 3. Ordens das cadeias

Duas ordens equivalentes, distribuídas igualmente entre as cadeias (metade em cada ordem,
por modo), para controlar efeito de ordem:

| Ordem | Sequência de pedidos |
|---|---|
| Ordem A | P1, P2, P3, P4, P5, P6, P7, P8, P9, P10 |
| Ordem B | P2, P1, P4, P3, P6, P5, P8, P7, P10, P9 |

**Justificativa:** a Ordem B inverte os pares de pedidos do mesmo tipo (cabe/tensiona),
mantendo o intercalamento entre tipos mas eliminando o viés de posição dentro do tipo.
A distribuição entre ordens é feita por sorteio antes da coleta, com semente fixa documentada
no log da coleta.

**Número de cadeias:** `_a preencher — estimativa de poder do piloto (cerca de 15-20 por modo)_`
**Distribuição:** `_n_` cadeias na Ordem A e `_n_` na Ordem B, por modo.

---

## 4. Definição operacional de regressão

Um passo regride quando **um teste de regressão que passou na execução imediatamente anterior
(passo p−1) falha na execução atual (passo p)**, sobre a mesma suíte rodada duas vezes para
descartar instabilidade (flaky). O resultado do passo é a média das duas rodadas.

Regras complementares:
- Teste que falhou desde o início (passo 0) não conta como regressão nos passos seguintes.
- Teste marcado como flaky (resultado diferente entre as duas rodadas do mesmo passo) é
  registrado como `flaky=1` e excluído do cômputo de regressão naquele passo.
- A suíte cobre as superfícies HTTP e interface web (data-testid).

---

## 5. Regra de passo falho

Se a execução do agente em um passo falhar (erro de runtime, timeout, saída sem commit):

1. **Uma nova tentativa sem feedback:** o agente recebe o mesmo pedido, sem ver o erro anterior.
2. **Se falhar novamente:** a cadeia termina. O passo é registrado como `run_ok=0` e todos os
   passos seguintes são `censurado=1`. Esses dados entram na análise de sobrevivência mas são
   excluídos das análises de regressão e violação.

---

## 6. Ajustes do piloto incorporados

`_A preencher após a decisão GO do relatório do piloto (issue #109)._`

| Ajuste | Descrição | Motivação |
|---|---|---|
| _(nenhum até aqui)_ | — | — |

---

## 7. Regra de protocolo

**Após a criação da tag `protocolo-v1`, qualquer mudança em pedidos ou nos testes é um
desvio.** Os dados coletados com o protocolo anterior e com o novo protocolo devem ser
analisados separadamente, ou os afetados devem ser descartados, conforme decisão do grupo e
registrado em `desvios.md`.

Essa regra vale também para mudanças no modelo ou na versão do Claude Code.

---

## 8. Revisão e concordância do grupo

| Papel | Membro | Concordou? |
|---|---|---|
| A (Planejamento) | @bernardordm | `_pendente_` |
| B (Coleta) | @DevMiguelDiniz | `_pendente_` |
| C (Análise) | @joaomarcelocpa | `_pendente_` |

> Este documento só pode receber a tag `protocolo-v1` quando os três membros concordarem
> e o relatório do piloto tiver decisão GO ou GO com ajustes incorporados.
