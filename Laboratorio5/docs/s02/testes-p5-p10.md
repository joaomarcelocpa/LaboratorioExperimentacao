# Testes de aceitação e implementação de referência de P5 a P10

Issue #117 (papel B). Mesma regra de P1 a P4: os testes são **ocultos** (fora do workspace do agente) e há uma **implementação de referência feita à mão**, que prova que os testes são satisfazíveis e não presos a uma estrutura.

## O que foi entregue

| Entregável | Onde | Observação |
|---|---|---|
| Testes de aceitação P5 a P10 | `tests/acceptance/src/test/java/labexp/aceitacao/p5` … `p10` | JUnit 5, HTTP e Playwright (`data-testid`) |
| Implementação de referência | `reference/` | Semente + P5 a P10, hexagonal, ArchUnit verde |
| Regressão atualizada | `tests/regression/` | cabeçalho `X-Papel: gestor` e troca de papel na tela (ver abaixo) |
| Execução reproduzível | `tests/acceptance/rodar.sh` | sobe a referência em H2, roda N rodadas |

**Ocultação.** O harness monta no container do agente apenas a cópia da semente. `tests/acceptance/` e `reference/` nunca devem ser montados (a referência é a resposta dos pedidos).

## Como rodar

```bash
cd Laboratorio5/tests/acceptance
./rodar.sh                       # referência em H2, P5..P10, 2 rodadas na mesma instância
./rodar.sh --regressao           # antes, a regressão inteira
./rodar.sh --pedidos "P5 P7"     # só alguns pedidos
./rodar.sh --externo             # aplicação já no ar em BASE_URL (ex.: PostgreSQL via docker compose)
```

- Pré-requisito de P9: a aplicação precisa ter `NOTIFICACAO_URL=http://<host>:9099/notificacoes`. O stub sobe dentro do próprio teste (porta `STUB_PORTA`, padrão 9099). `rodar.sh` e `reference/docker-compose.yml` já configuram isso.
- O script falha se nenhum teste for executado: um filtro que não seleciona nada passaria em silêncio.
- Banco: quem decide é quem sobe a aplicação (perfil `h2` ou `DATABASE_URL`). Os testes só usam HTTP, então valem para os dois (P10).

## Casos de teste por pedido (nomes definitivos)

Os nomes seguem o rastreio dos pedidos, com a grafia de `Conclussao` corrigida. O rastreio de `docs/s02/pedidos/P5.md` a `P10.md` ainda diz "a atualizar com nomes definitivos"; essa troca é do papel A, que é dono desses arquivos.

| Pedido | Fronteira | Casos |
|---|---|---|
| P5 | HTTP | `historico_registra_alteracoes_com_metadados`, `historico_registra_conclusao`, `historico_tarefa_inexistente_retorna_404`, `historico_persiste_apos_exclusao` |
| P6 | HTTP e interface | `gestor_pode_executar_todas_operacoes`, `colaborador_recebe_403_em_operacoes_restritas`, `sem_cabecalho_usa_papel_colaborador`, `interface_mostra_papel_e_oculta_botoes_para_colaborador`, `interface_exibe_botoes_para_gestor` |
| P7 | HTTP | `reenvioComMesmaChaveNaoDuplica`, `chaveComPayloadDiferenteRetorna422`, `semChaveIdempotenciaFuncionaNormal`, `listagemConfirmaUnicaTarefaAposReenvio` |
| P8 | HTTP e interface | `relatorioBateComEstadoInserido`, `distribuicaoPorResponsavelCorreta`, `telaDeListagemContinuaFuncionando`, `relatorioBaseVaziaRetornaZeros` |
| P9 | interface | `notificacaoEnviadaComSucesso`, `notificacaoFalhoNaoImpedeConclusao`, `timeoutNaoImpedeConclusao`, `reenvioManualFunciona` |
| P10 | HTTP | `aplicacaoIniciaComH2SemErro`, `crudCompletoFuncionaComH2`, `cargaEmParaleloPersisteTudo` |

## Como os testes evitam acoplamento

Os pedidos fixam o que deve ser observável, mas não os nomes das propriedades JSON. Os testes não inventam um formato:

- `Json` lê de forma tolerante: o histórico aceita `valorAnterior`/`anterior`/`antigo`…, o timestamp é qualquer campo com data ISO, a lista pode vir pura ou embrulhada, e os contadores do relatório são achados em `{"pendentes":5}`, `{"porStatus":{"PENDENTE":5}}` ou `[{"status":"PENDENTE","total":5}]` (lista conta pelo tamanho).
- Nenhum teste usa rota, camada, fila, índice ou modelagem fora do que o pedido declara. A única rota extra assumida é a da própria semente (`/tarefas`, `/concluir`, `/health`).
- Dados entram só pelos endpoints existentes, em paralelo (`Base.emParalelo`). Nenhum teste toca o banco.
- Cada teste usa responsável e título únicos e limpa o que criou. Só P8 esvazia a base (os critérios "base vazia" e contadores exatos exigem isso).
- Papel: a carga e a limpeza agem sempre como `gestor`, para o P6 não quebrar os demais.

## Decisões onde o texto dos pedidos deixa margem

Cada item abaixo é uma leitura adotada nos testes e um apontamento para o papel A (auditoria cruzada), que pode pedir ajuste de texto ou de teste.

1. **P5, exclusão × 404.** "Histórico de tarefa inexistente retorna 404" e "excluir não apaga o histórico por pelo menos 1 segundo" se tocam: uma tarefa excluída é inexistente? Os testes leem 200 com as entradas logo após excluir e de novo após 900 ms (dentro da janela de 1 s), e 404 só para um id que nunca existiu.
2. **P5, atualização.** Cada teste altera um único campo por atualização (`titulo`, depois `responsavel`), o que torna "2 atualizações = 2 entradas" independente de a implementação registrar uma entrada por campo ou por atualização. Criar não gera entrada.
3. **P6, como o usuário troca de papel na tela.** O pedido só diz que `papel-usuario` "mostra o papel ativo". `PapelNaTela` tenta `?papel=`, depois campo editável ou lista de opções, e falha com mensagem explícita se nenhum funcionar. Se o texto não for ajustado, é a decisão com maior risco de reprovar uma solução correta.
4. **P6, interface.** Para colaborador: sem formulário de criação, sem `botao-editar` e `botao-excluir`, com `botao-concluir` visível.
5. **P8, leitura do exemplo.** "5 pendentes, 3 concluídas e 2 vencidas e pendentes" foi lido como 8 tarefas, sendo 2 das 5 pendentes vencidas. As 3 concluídas também têm prazo vencido para provar que concluída não conta como vencida.
6. **P8, formato.** O JSON dos agregados não é definido; ver a leitura tolerante acima. A interface do relatório e a do histórico não têm caminho de navegação definido (só o `data-testid`), então P5 e P8 são verificados por HTTP, o plano B da issue; só a listagem de P8 usa a tela.
7. **P9, contrato do stub contraditório.** O texto diz "200 nas de número par (1ª, 3ª, 5ª…)" e a tabela diz que par (2ª, 4ª…) responde 200 e ímpar 503. As duas leituras se contradizem. Para o teste não depender disso, o stub dos testes tem modos escolhidos pelo teste (200, 503, lento) em vez de contar requisições. Convém corrigir o texto antes do congelamento.
8. **P9, URL.** Não diz se `NOTIFICACAO_URL` é base ou endpoint completo. O stub aceita POST em qualquer caminho.
9. **P9, só pela tela.** O status da notificação só é observável em `status-notificacao`, então os quatro casos dirigem a interface. O status pode estar dentro do item da tarefa ou numa área única (os dois funcionam). O caso de timeout exige que `concluir` responda em menos de 3,5 s com o stub levando 4 s.
10. **P10, banco não observável por HTTP.** Nenhum teste consegue provar qual banco está ativo sem acessar o banco, o que é vedado. O critério "a suíte inteira passa no perfil `h2`" é verificado rodando P5 a P9 e a regressão com a aplicação nesse perfil. Os testes de P10 não distinguem um H2 de um PostgreSQL, e passam também na semente pura, como deve ser para uma sonda de ausência de regressão.

## Regressão atualizada

Os comportamentos acumulados por P5 a P10 que mudam o que a regressão enxerga:

- **P6:** o papel padrão passa a ser colaborador, que não cria, edita nem exclui. `ApiClient` da regressão envia `X-Papel: gestor` sempre (ignorado antes de P6) e `PapelNaTela.comoGestorSeExistir` coloca a tela no papel gestor quando existe o campo `papel-usuario`.
- **P7 a P9:** cabeçalhos e rotas novas são opcionais; a regressão não precisa de mudança. Sem `NOTIFICACAO_URL` o concluir continua respondendo 200.
- **P10:** a regressão roda inalterada nos dois bancos.

Em cada passo n da coleta, a verificação do passo roda a regressão e a aceitação de P1 a Pn.

## Evidências

| Verificação | Resultado |
|---|---|
| Aceitação P5 a P10 contra `reference/` (H2), 2 rodadas na mesma instância | 24/24 e 24/24 |
| P9 com falha injetada de forma determinística (stub 503 e lento) | estável nas duas rodadas |
| Regressão (`tests/regression`) contra `reference/` | 29/29 |
| Testes unitários e ArchUnit de `reference/` | 42/42, zero violações |
| Aceitação contra a semente pura (verificação negativa) | 17 de 21 casos de P5 a P9 falham; os 4 que passam são os que descrevem comportamento já presente: 404 de histórico de id desconhecido, gestor faz tudo, criar sem `Idempotency-Key`, listagem de tarefas |
| P10 contra a semente pura | passa, como esperado |

## Pendências e limites

- **P1 a P4:** a issue #105 está fechada, mas `tests/acceptance/P1` a `P4`, o `reference/` de P1 a P4 e o harness não estão no `main` nem em nenhuma branch remota. Por isso `reference/` aqui é a semente mais P5 a P10, e "a regressão de P1 a P4 continua verde" **não foi verificado contra uma referência de P1 a P4**. A pasta `tests/acceptance/` segue o mesmo desenho e deve receber `p1` a `p4` quando esses testes forem versionados.
- **PostgreSQL:** o daemon do Docker não estava disponível, então o perfil padrão (PostgreSQL) da referência não foi executado. As migrações usam `timestamp with time zone` e `generated by default as identity`, aceitos por PostgreSQL e H2, mas isso está **por verificar** com `docker compose up` em `reference/` e `./rodar.sh --externo`.
- **Validação por papel A:** os testes de P5 a P10 ainda não foram lidos por quem escreveu os pedidos (A), e o item "validados por papel A" do checklist depende disso. Os apontamentos da seção de decisões são o roteiro.
