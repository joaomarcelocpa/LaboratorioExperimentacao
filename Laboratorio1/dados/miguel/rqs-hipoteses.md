RQ06 — Sistemas populares possuem um alto percentual de issues fechadas?

Métrica: razão entre issues fechadas e total de issues (closedIssues / totalIssues).

Hipótese: Sim. Espera-se que sistemas populares apresentem uma razão alta de issues fechadas sobre o total

Justificativa: Repositórios populares tendem a ter comunidades ativas e mantenedores dedicados, com processos estabelecidos de triagem (labels, templates, bots de stale). Alto volume de contribuidores acelera o fechamento, e projetos maduros costumam encerrar issues antigas em vez de deixá-las acumular. Ainda assim, a própria popularidade gera um influxo grande de issues novas (dúvidas, pedidos de feature, duplicatas), o que pode manter uma fração relevante em aberto.

Política de divisão por zero: repos com totalIssues == 0 serão excluídos do cálculo da razão (razão indefinida), e sua quantidade será reportada à parte.

RQ07 — Linguagens mais populares recebem mais contribuição, releases e atualizações?

Métricas: RQ02 (total de pull requests aceitas), RQ03 (total de releases) e RQ04 (tempo até a última atualização), agrupadas por linguagem primária.

Hipótese geral: Parcialmente. Espera-se que repositórios em linguagens mais populares tendam a receber mais contribuição externa e a ser atualizados com mais frequência, mas não necessariamente a lançar mais releases — a frequência de releases parece mais ligada à cultura de cada ecossistema do que à popularidade da linguagem.

Hipótese (contribuição externa — RQ02): linguagens mais populares recebem mais pull requests aceitas, porque uma base maior de desenvolvedores familiarizados com a linguagem amplia o pool de potenciais contribuidores externos.

Hipótese (releases — RQ03): não se espera diferença clara. A frequência de releases depende mais das convenções do ecossistema e da ferramenta de build/publicação (ex.: npm, PyPI, Cargo) do que da popularidade da linguagem em si.

Hipótese (atualização — RQ04): linguagens mais populares são atualizadas com mais frequência (menor tempo desde o último push), pois maior atividade da comunidade e mais contribuidores implicam commits mais frequentes.

Fonte de "linguagens populares": a mesma referência definida na RQ05 (ex.: GitHub Octoverse), mantida em todo o laboratório.

Comparação: medianas de RQ02, RQ03 e RQ04 agrupadas por linguagem, comparando o conjunto de linguagens populares contra as demais.