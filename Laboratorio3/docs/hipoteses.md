# Hipóteses do Estudo — [B]: RQ 02, 03b e 08a

Escritas antes de qualquer análise de dados, como exigido pelo aceite da Issue #38.

## RQ 02 — Lead time for changes

**Hipótese:** Repositórios populares open-source apresentam mediana de lead time
entre 1 e 7 dias (categoria "High" na escala DORA). A hipótese é que projetos
maduros tendem a acumular commits em branches de feature por alguns dias antes
de uma release, mas raramente ficam semanas sem publicar.

A variante por commit (b) deverá ser menor que a variante por release (a),
pois commits recentes puxam a mediana para baixo enquanto um único commit
antigo inflaciona apenas a variante (a).

## RQ 03b — Change Failure Rate por release corretiva

**Hipótese:** A maioria dos repositórios terá CFR(b) abaixo de 30% (faixa
"High"), com mediana próxima de 15%. A lógica é que projetos com CI/CD ativo
já filtram defeitos antes da release; quando chegam ao usuário, correções
urgentes de patch são a exceção, não a regra.

Esperamos que projetos com maior frequência de releases apresentem CFR(b)
mais baixo, pois cada release carrega menos mudanças e o risco individual é
menor.

## RQ 08a — Rework rate (bônus DORA 2024)

**Hipótese:** O rework rate (sem limite de dias) será sistematicamente maior
que o CFR(b) (janela de 7 dias), pois captura correções tardias que aparecem
semanas depois. Estimamos que a diferença seja de pelo menos 5 p.p. na
mediana da amostra.

A métrica confirmará que o CFR(b) com 7 dias subestima a proporção real de
releases problemáticas, o que é uma ameaça à validade que deve ser discutida
no artigo.

---

# Hipóteses do Estudo — [A]: RQ 01, 06 e 07

Escritas antes de qualquer análise de dados, como exigido pelo aceite da Issue #38.

## RQ 01 — Deployment frequency

**Hipótese:** A mediana de releases por semana ficará entre 0,25 e 1, ou seja,
entre Medium e High na tabela de referência. Poucos repositórios chegarão a
Elite (7 ou mais por semana). A amostra já exige pelo menos 5 releases por ano,
mas projetos populares de código aberto costumam publicar de forma
episódica, em lotes quando uma versão fica pronta, e não de forma contínua.
Quem publica todo dia costuma fazer deploy de um serviço, e não release
versionada de uma biblioteca.

Esperamos uma distribuição muito assimétrica à direita: o IQR deve ser
largo e a média bem acima da mediana, puxada por poucos repositórios que
publicam quase todo dia. Por isso reportamos mediana e IQR.

A contagem por tag deve render frequência maior ou igual à por release, pois
nem toda tag vira release no GitHub. Projetos que só marcam tags ficam com
frequência de release próxima de zero.

## RQ 06 — Fatores associados ao desempenho DORA

**Hipótese:** A maior parte das associações será fraca. Esperamos tamanhos de
efeito pequenos (ε² abaixo de 0,06) e, depois da correção de Holm, poucos
testes significativos entre os 12 ou mais que faremos. Os fatores que mais
devem se destacar são:

- **Automação de release** (semantic-release, release-please, changesets,
  goreleaser): associada a maior frequência de releases e a menor lead time.
  Automatizar tira o custo manual de publicar, e isso deve se refletir
  direto na cadência.
- **Uso de Conventional Commits:** deve andar junto com a automação, porque
  várias dessas ferramentas leem o padrão. Esperamos que o efeito sobre as
  métricas DORA seja menor do que o da automação em si, já que parte dele é
  só a mesma informação.
- **Número de contribuidores:** mais contribuidores, maior frequência de
  releases, pois há mais mudanças prontas para sair. Esperamos que isso não
  melhore o CFR, que pode até piorar com mais gente mexendo no código.
- **Linguagem:** ecossistemas com gerenciador de pacotes e cultura de
  versionamento frequente (JavaScript/TypeScript e Go) devem ter frequência
  maior do que C e C++, que publicam em ciclos mais longos.

Esperamos efeito pequeno ou nulo de **popularidade** (estrelas) e de **idade**
do repositório. Estrelas medem visibilidade, não práticas de entrega, e
repositórios mais velhos podem ser tanto mais maduros quanto mais lentos.
Não temos hipótese direcional forte para a idade.

## RQ 07 — Sensibilidade da classificação DORA à definição operacional

**Hipótese:** A classificação dependerá de forma relevante da definição
escolhida. Esperamos que entre 30% e 50% dos repositórios mudem de categoria
em pelo menos um dos pares de combinações (C1×C2, C1×C3, C2×C3), e kappa
ponderado de concordância moderada, entre 0,3 e 0,6. Não esperamos
concordância quase perfeita.

A maior parte da mudança deve vir de duas escolhas:

- **Lead time (a) contra (b):** a variante por commit é menor do que a por
  release, como na hipótese da RQ 02, o que pode empurrar o repositório uma
  classe acima nessa métrica.
- **Unidade de deploy (release contra tag):** a contagem por tag é maior e
  pode subir a nota de frequência.

Esperamos que a escolha de CFR (a contra b) mude a classe com menos
frequência do que as duas anteriores. A nota de CFR tem faixas largas
(15 pontos percentuais), então diferenças pequenas entre os dois proxies
tendem a cair na mesma classe.

Se a hipótese estiver certa, as conclusões das RQ 01 a 06 só valem
condicionadas à definição operacional, e isso entra como ameaça à validade.

---

# Hipóteses do Estudo — [C]: RQ 03a, 04, 05 e 08b

Registradas em 14/10/2026, **depois** da rodada de coleta. O texto parte das
hipóteses informais do plano da sprint (T2) e não foi ajustado a nenhum
resultado; ainda assim, como o registro é posterior à coleta, isso deve constar
na seção de ameaças à validade.

## RQ 03a — Taxa de falha no CI

**Hipótese:** A mediana da taxa de falha das execuções de CI no *default
branch* ficará entre 10% e 25%. Parte relevante dessas falhas, porém, não deve
ser atribuível ao código: testes instáveis (*flaky*), indisponibilidade de
*runners* e dependências externas fazem a mesma versão do código falhar e
depois passar. Por isso, esperamos que a taxa caia de forma perceptível quando
desconsideramos as falhas seguidas de sucesso no mesmo *commit*.

Esperamos também que esse proxy superestime a taxa de falha em produção
definida pelo DORA, pois uma falha de *pipeline* impede a entrega antes que ela
chegue ao usuário.

## RQ 04 — Tempo de recuperação

**Hipótese:** A mediana do tempo de recuperação após uma falha de CI ficará
abaixo de um dia, o que colocaria a maior parte dos repositórios na faixa
*High*. Um *default branch* quebrado bloqueia todos os contribuidores, o que
cria um incentivo forte para corrigi-lo rapidamente.

Ainda assim, esperamos uma cauda longa: alguns repositórios devem conviver com
*workflows* quebrados por semanas, e uma parcela não desprezível dos episódios
deve terminar censurada no fim da janela. Ao excluir os episódios compostos
apenas de falhas instáveis, que costumam se resolver com uma simples
reexecução, esperamos que a mediana aumente, refletindo o tempo necessário para
corrigir falhas reais.

## RQ 05 — Velocidade versus estabilidade

**Hipótese:** Seguindo a afirmação do DORA de que velocidade e estabilidade não
são um *trade-off*, esperamos uma correlação de Spearman fraca e negativa entre
a frequência de deploys e a taxa de falha: projetos que publicam com mais
frequência tendem a ter processos de entrega mais automatizados e mudanças
menores.

Esperamos, contudo, que a magnitude seja pequena (|ρ| < 0,3), já que a
frequência de releases em projetos *open-source* depende também de fatores
alheios à qualidade do processo, como o tipo de projeto e a política de
versionamento.

## RQ 08b — Evolução temporal

**Hipótese:** A maioria dos repositórios não apresentará tendência
estatisticamente significativa na taxa de falha de CI nem no tempo de
recuperação ao longo dos doze meses da janela, pois mudanças de processo
costumam ser lentas e esse período é curto para detectá-las.

Entre os repositórios com tendência significativa, esperamos mais casos de
melhora do que de piora, já que projetos populares e maduros tendem a
estabilizar seus *pipelines* com o tempo.
