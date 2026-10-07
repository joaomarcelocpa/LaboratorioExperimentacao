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
