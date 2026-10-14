# Protocolo de desempate da conferência manual

Vale para as três perguntas da amostra-ouro: tipo do projeto, entregas reais
e release corretiva. Os três avaliadores (João, Bernardo e Miguel) respondem
sozinhos. Depois disso, a resposta final de cada item é definida assim.

## Regra

| Respostas dos três | Situação | Resposta final |
|---|---|---|
| Todas iguais (3-0) | unânime | a resposta dada |
| Duas iguais e uma diferente (2-1) | maioria | a resposta das duas |
| Três diferentes (1-1-1) | empate | decidida em reunião |

Só pode haver empate nas perguntas com mais de duas opções (tipo do projeto e
entregas reais). Em `corretiva` (sim ou não) sempre há maioria.

## Como decidir um empate

1. Rodar `python -m conferencia.consenso`. Ele escreve
   `data/conferencia/empates_para_reuniao.csv` com só os itens sem maioria e as
   três respostas de cada um.
2. Na reunião, os três abrem o link do item, leem de novo e discutem. Cada um
   explica o motivo da sua resposta antes de qualquer voto.
3. Se o grupo chegar a uma resposta, ela é registrada em
   `data/conferencia/desempates.csv`, com as colunas
   `dimensao,repo,tag,valor`. Para as perguntas por repositório, `tag` fica em
   branco.
4. Se ainda não houver acordo, vale `incerto` em `entregas_reais`. Em
   `tipo_projeto`, vale `outro`.
5. Rodar o consenso de novo. Os itens decididos passam a constar como
   `desempate` em `divergencias.csv`.

## O que não se faz

- Não se muda uma resposta individual depois de ver a dos outros. Os arquivos
  `rotulos_<nome>_*.csv` ficam como foram entregues. Mudanças vão só em
  `desempates.csv`.
- Não se desempata usando o resultado da heurística automática. O desempate
  é humano.

## Como o kappa é calculado

O kappa de Fleiss (`python -m conferencia.kappa`) usa as **respostas
individuais**, antes do desempate. Ele mede se o critério é claro, e o desempate
não deve melhorar esse número. O resultado fica em `data/conferencia/kappa.csv`,
uma linha por pergunta, com a leitura das faixas de Landis e Koch (1977):

| Kappa | Concordância |
|---|---|
| até 0,20 | leve |
| 0,21 a 0,40 | razoável |
| 0,41 a 0,60 | moderada |
| 0,61 a 0,80 | substancial |
| acima de 0,80 | quase perfeita |

Um kappa baixo não é falha do trabalho: indica que o critério é ambíguo, e isso
é descrito como achado no artigo.

Se todos responderem a mesma categoria em todos os itens, o kappa fica
indefinido (não há variação para medir). O script avisa nesse caso.
