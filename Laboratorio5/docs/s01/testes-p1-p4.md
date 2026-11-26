# Testes de aceitação e implementação de referência de P1 a P4

Issue #105 (papel B), parte "testes ocultos e referência". O harness está em `docs/s01/harness.md`. Mesmas regras de P5 a P10 (`docs/s02/testes-p5-p10.md`): testes **ocultos** (fora do workspace do agente), referência **feita à mão**, nenhum teste acessa o banco, carga de dados só por endpoints existentes e em paralelo.

## O que foi entregue

| Entregável | Onde |
|---|---|
| Testes de aceitação P1 a P4 | `tests/acceptance/src/test/java/labexp/aceitacao/p1` … `p4` |
| Implementação de referência | `reference/` (semente + P1 a P10, uma só base de código) |
| Execução | `tests/acceptance/rodar.sh --pedidos "P1 P2 P3 P4"` |

`reference/` e `tests/acceptance/` nunca podem ser montados no container do agente.

## Casos de teste (nomes definitivos)

Os nomes seguem o rastreio dos pedidos, com a grafia corrigida onde havia erro de digitação (`tarefaConcluídaNaoGeraAviso`, `…ErrosESuccessos`, `…Viveis…`, `telaRespondeduranteImportacao`). O rastreio dos arquivos `P1.md` a `P4.md` ainda diz "sugestões"; trocar é do papel A.

| Pedido | Fronteira | Casos |
|---|---|---|
| P1 | interface | `avisoApareceDentroDoTempoAposVencimento`, `tarefaConcluidaNaoGeraAviso`, `tarefaGeraNoMaximoUmAviso` |
| P2 | HTTP | `filtroRespondeDentroDoTempoComGrandeVolume`, `filtroRetornaTodosOsResultados`, `ordenacaoPorVencimentoCorretaNosExtremos` |
| P3 | HTTP e interface | `empresaBNaoVeTarefasDaEmpresaA`, `empresaBRecebe404AoAcessarTarefaDaEmpresaA`, `tarefasAntigasVisiveisNaEmpresaPadrao`, `semCabecalhoFuncionaComoAntes`, `interfaceIsolaPorEmpresa` |
| P4 | interface | `importacaoContaCorretamenteErrosESucessos`, `telaRespondeDuranteImportacao`, `linhasInvalidasNaoGeramTarefasParciais` |

## Onde o texto dos pedidos deixa margem (apontamentos para o papel A)

P3 e P4 definem identificadores; **P1 e P2 não definem nenhum**, e P4 não define rota HTTP. Cada leitura abaixo está nos testes e pode ser trocada por uma correção de texto.

1. **P1, como chegar à tela de Avisos.** Só há o `data-testid="lista-avisos"`. O teste aceita a lista na própria página ou atrás de um link ou botão com o texto "Avisos". Não há rota HTTP de avisos no pedido, então P1 é verificado só pela tela.
2. **P1, negativo.** "Não gera aviso" não se prova só esperando. O caso da tarefa concluída cria também uma tarefa de controle com o mesmo vencimento; só depois que o aviso do controle aparece, e mais 2 s, confere-se que a concluída não tem aviso.
3. **P2, nomes dos parâmetros.** O pedido não fixa como filtrar nem ordenar. Os testes assumem os nomes naturais da API da semente: `responsavel` e `status` (`PENDENTE`/`CONCLUIDA`) em `GET /tarefas`, e mandam a ordenação sob vários apelidos ao mesmo tempo (`ordenar`, `ordem`, `ordenarPor`, `sort`, `orderBy` = `vencimento`). Uma solução correta que use outros nomes reprova. **É o apontamento mais importante de P1 a P4:** convém acrescentar um "mínimo observável" a P2.
4. **P2, "alcançáveis" e paginação.** Conta-se a lista devolvida; numa resposta paginada aceita-se um campo de total (`total`, `totalElements`, `count`).
5. **P2, "primeiro resultado em até 1 s".** Medido como a **mediana de 3 chamadas** da resposta HTTP completa, depois de uma de aquecimento, não o tempo de renderização na tela.
6. **P2, volume.** 50.000 tarefas, carregadas em paralelo (16 threads) e apagadas no fim. `P2_VOLUME` reduz o volume só para depurar os testes; o valor oficial é o padrão.
7. **P3, empresa padrão.** O texto não diz o nome da empresa padrão. "Tarefas criadas antes da mudança" são lidas como tarefas criadas **sem** o cabeçalho, visíveis para quem não o envia e invisíveis para outra empresa.
8. **P3, interface.** O teste preenche `empresa-input` e aceita Enter, perda de foco ou mudança do campo como forma de aplicar.
9. **P4, confirmar.** "Escolhe um arquivo e confirma" não define o botão de confirmação. Depois de selecionar o arquivo, o teste clica no primeiro botão visível cujo nome case com *importar*, *confirmar* ou *enviar*, se houver (se a importação disparar ao escolher o arquivo, nada é clicado).
10. **P4, formato.** O CSV usa o cabeçalho `titulo,responsavel,vencimento` e vencimento ISO-8601 em UTC (o formato da própria API). "Vencimento fora do formato" usa o texto `amanha`. O pedido não fixa nem o formato de data nem o cabeçalho.
11. **P4, numeração das linhas e "20.000 linhas".** São 20.000 linhas de dados mais o cabeçalho. O número do erro pode ser contado pelo arquivo (cabeçalho = linha 1) ou pelos dados; o teste aceita as duas numerações, mas exige **exatamente** as 50 linhas inválidas. Os números são lidos depois da palavra "linha"; se o formato não tiver essa palavra, usa-se todos os números da área.
12. **P4, resposta da tela.** Verifica-se também, por HTTP, quantas tarefas existem de fato (19.950), para o teste não depender só do texto mostrado.
13. **P4, "a tela continua respondendo".** Durante a importação o teste faz consultas por HTTP (cada uma em menos de 1,5 s) e digita no formulário, conferindo que o valor digitado aparece. Se a importação terminar muito rápido, o teste passa trivialmente: a janela de observação é curta por natureza.

Os testes de P1 a P4 criam o estado pela API como gestor e, quando usam a tela para criar ou importar, colocam a tela no papel gestor com a mesma regra do P6 (`PapelNaTela.comoGestorSeExistir`).

## Referência

`reference/` é uma única base de código com P1 a P10, hexagonal e com as regras ArchUnit verdes.

- **P1:** os avisos nascem na consulta: `GET /avisos` cria o aviso de toda tarefa pendente já vencida que ainda não tem um (chave primária por tarefa, então no máximo um), e a tela consulta a cada 2 s.
- **P2:** `GET /tarefas?status=&responsavel=&ordenar=vencimento` com índice por empresa, responsável, status e vencimento.
- **P3:** a empresa vem de `X-Empresa` (padrão `padrao`) e é fixada por filtro de entrada; toda leitura e escrita da persistência filtra por ela. A coluna nova tem valor padrão, então as tarefas antigas ficam na empresa padrão.
- **P4:** `POST /tarefas/importacao` com o CSV no corpo; as linhas válidas entram em lote e as inválidas voltam com número e motivo. A tela tem `importar-csv`, um botão de confirmar e `resultado-importacao`.
- **P6 e a importação:** a importação conta como "criar" e exige gestor.

## Evidências

| Verificação | Resultado |
|---|---|
| Aceitação P1 a P4 contra `reference/` (H2), 2 rodadas na mesma instância | 14/14 e 14/14 (junto de P5 a P10: 38/38) |
| P2 com 50.000 tarefas e P4 com 20.000 linhas | volumes oficiais, estáveis nas duas rodadas |
| Regressão e unitários/ArchUnit de `reference/` | regressão verde; 45/45 unitários, zero violações |
| Aceitação contra a semente pura (verificação negativa, com `P2_VOLUME=1000` e `P4_LINHAS=1000`) | 12 de 14 falham; passam só a medição de tempo de P2 (a semente é rápida com 1.000 tarefas) e `semCabecalhoFuncionaComoAntes` |

## Limites

- A referência foi executada em H2. O perfil padrão (PostgreSQL) não foi exercitado (o Docker está desligado nesta máquina).
- Os testes de P1 a P4 ainda não foram lidos pelo papel A, que é o revisor da issue.
