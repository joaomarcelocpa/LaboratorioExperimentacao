# Metodologia — [B]: Entrega, Lead Time e CFR

Escrita para a Issue #67 (Sprint S02).

---

## Unidade de entrega (*deploy proxy*)

O GitHub não registra deploys em produção. Usamos **release publicada** como
proxy de deploy: um objeto do tipo *release* com `draft = false` e
`published_at` dentro da janela de observação. Pré-releases (`prerelease =
true`) e tags sem release associada ficam de fora da definição principal; elas
aparecem como variantes na RQ 07.

Essa escolha subestima a frequência de entrega de repositórios que operam como
serviços e fazem deploys contínuos sem publicar releases, e a superestima em
bibliotecas que publicam releases automáticas a cada push. Esse viés é ameaça à
validade de construto e é discutido na seção correspondente.

---

## Lead time for changes (RQ 02)

Para cada release R da janela que possui release anterior, obtemos os commits
incluídos via `GET /repos/{owner}/{repo}/compare/{anterior}...{R}`. Releases
sem predecessor — a primeira da história do repositório — não entram no cálculo.

### Variante (a) — por release

O lead time de R é `publicada_em(R) − data_autor(commit mais antigo de R)`. O
valor do repositório é a **mediana** das suas releases na janela.

### Variante (b) — por commit

Cada commit c incluído em R contribui com `publicada_em(R) − data_autor(c)`. O
valor do repositório é a **mediana** de todos os commits de todas as suas
releases na janela. A variante (b) é menos sensível a um único commit antigo
"esquecido" numa release, que inflaciona a variante (a) sem representar demora
real no processo de entrega.

### Variante `lt_commit_base_recente`

Releases cuja base (release anterior) foi publicada há mais de **1 ano** são
excluídas antes de calcular a mediana por commit. A motivação é que o intervalo
entre a base e a release atual domina o lead time de todos os commits incluídos,
criando um viés para repositórios que ficaram dormentes por um longo período
antes de publicar uma versão nova. A variante serve de comparação para verificar
o quanto esse viés afeta o resultado geral.

O campo `data_autor` vem de `commit.author.date`, que registra quando a mudança
foi escrita. Rebases e *squash merges* podem distorcer essa data; isso é
registrado como ameaça à validade de construto.

---

## Change Failure Rate — variante (a): proxy de CI (RQ 03a)

**CFR(a)** é calculado sobre os workflow runs do *default branch* disparados por
`push`, dentro da janela, com `conclusion` em `failure`, `timed_out` ou
`startup_failure`. Runs com `conclusion` em `cancelled`, `skipped`, `neutral`,
`action_required` ou `stale` são ignorados.

```
CFR(a) = falhas / (falhas + sucessos)
```

Essa variante mede **falha de pipeline**, não falha em produção: uma execução
que falha impede a entrega antes que ela chegue ao usuário, o que
provavelmente subestima a taxa de falha real em produção. A diferença entre as
duas variantes (a) e (b) é objeto da RQ 05.

Adicionalmente, reportamos:

- **CFR(a) bruto**: inclui todas as tentativas de cada run (não só a final).
- **CFR(a) sem flaky**: exclui falhas em que o mesmo `head_sha` produziu um
  sucesso posterior no mesmo workflow, tratando-as como instabilidades de
  infraestrutura.
- **pct_falhas_flaky**: proporção das falhas brutas que são flaky; indica o
  quanto o CFR bruto é inflado por problemas de ambiente.

---

## Change Failure Rate — variante (b): proxy de release corretiva (RQ 03b)

**CFR(b)** considera uma release R como **falha** se ela for seguida, em até
**7 dias**, por uma *release corretiva*. O denominador exclui releases
publicadas nos últimos 7 dias da janela, que não tiveram tempo suficiente para
receber uma correção (*censura*).

```
CFR(b) = releases que falharam / releases avaliadas
```

### Heurística de release corretiva

Uma release é classificada como corretiva com base em sinais extraídos da
comparação entre ela e a release imediatamente anterior. Cinco variantes foram
desenvolvidas e validadas:

| Variante | Critério |
|---|---|
| **v1** | só o número de *patch* mudou (`x.y.Z → x.y.Z+1`) **OU** algum commit contém `fix`, `hotfix` ou `revert` |
| **v2** | só patch mudou **OU** algum commit contém `hotfix` ou `revert` (exclui `fix` simples) |
| **v3** | só patch mudou **OU** mais de 20% dos commits contêm `fix`/`hotfix`/`revert` |
| **v4** | v1 **OU** as notas da release contêm palavra-chave de correção (`fix`, `bug`, `hotfix`, `revert`, `regression`, `patch`, `security`, `vulnerability`, `cve`, `crash`) |
| **v5** (adotada) | só patch mudou **OU** algum commit contém `hotfix`/`revert` **OU** mais de 15% dos commits contêm `fix`/`hotfix`/`revert` **OU** notas contêm palavra-chave de correção |

A v5 reduz os falsos positivos da v1 causados por releases com um único commit
`fix: typo` entre dezenas de features, sem sacrificar recall: exige um sinal
quantitativo mínimo (>15%) ou um sinal forte explícito (`hotfix`/`revert` ou
notas).

### Validação da heurística

Cada membro do grupo rotulou independentemente as 300 releases da amostra-ouro
(60 repositórios × 5 releases), lendo as notas e os commits sem consultar os
outros e sem ver a saída da heurística. A tabela abaixo mostra precisão,
recall e F1 de cada variante comparados a esses rótulos.

A coluna **"todos"** inclui as primeiras releases de cada repositório na
amostra, para as quais o pipeline não possui release anterior e portanto nunca
aplica a heurística. A coluna **"decidíveis"** exclui essas 60 primeiras
releases e reflete a comparação justa com o comportamento real do pipeline (240
releases avaliadas).

| Variante | F1 (todos) | P (todos) | R (todos) | F1 (decidíveis) | P (decidíveis) | R (decidíveis) |
|---|---|---|---|---|---|---|
| v1 | 0,595 | 0,439 | 0,923 | 0,604 | 0,443 | 0,949 |
| v2 | 0,537 | 0,493 | 0,590 | 0,535 | 0,519 | 0,551 |
| v3 | 0,594 | 0,474 | 0,795 | 0,605 | 0,487 | 0,796 |
| v4 | 0,598 | 0,438 | 0,940 | 0,607 | 0,442 | 0,969 |
| **v5** | **0,623** | **0,466** | **0,940** | **0,638** | **0,475** | **0,969** |

A v5 supera todas as outras em F1 tanto na coluna "todos" quanto na
"decidíveis". O recall muito alto (0,940 / 0,969) indica que a heurística
perde poucos positivos reais; a precisão mais baixa (0,466 / 0,475) reflete
casos em que uma release de feature com patch bump e poucas mensagens de
`fix` aciona a regra indevidamente. O F1 final ficou abaixo do limiar de 0,70
da especificação, reflexo do desacordo moderado entre os avaliadores na
dimensão `corretiva` (kappa de Fleiss = 0,661); Bernardo rotulou 171 releases
como corretivas contra 112 de João e 111 de Miguel, e o consenso por maioria
ficou em 117. Em contexto de incerteza de rótulo, o alto recall de v5 é
preferível a uma versão mais restritiva que reduz F1 penalizando recall.

O script `python -m metricas.validacao_heuristica` reproduz a tabela a partir
de qualquer arquivo de rótulos no mesmo formato de `planilha_releases.csv`.

### CFR(b) segmentado por esquema de versão

Repositórios que adotam Versionamento Semântico (`x.y.z`) beneficiam-se do
sinal de *patch-bump*; os demais dependem exclusivamente dos commits e das
notas. Na amostra de validação, o CFR(b) segmentado pela v1 foi:

| Grupo | Releases | CFR(b) |
|---|---|---|
| SemVer (`x.y.z`) | 289 | 81,7% |
| Não-SemVer | 11 | 90,9% |

O resultado deve ser interpretado com cautela para o grupo não-SemVer: apenas
11 releases na amostra de validação. Os valores agregados de toda a amostra
estão em `metricas.csv` nas colunas `cfr_b_semver` e `cfr_b_nao_semver`.

---

## Monorepos e lead time por tag (Issue #63)

### Monorepos

Repositórios com vários pacotes independentes no mesmo *repo* (monorepos)
publicam tags por pacote — por exemplo `packages/ui@2.1.0` e
`packages/api@3.0.0`. Isso distorce a frequência de releases e o lead time,
pois um commit de um pacote inflaciona as métricas de outro.

**Decisão adotada:** monorepos identificados são **registrados como ameaça à
validade**, não removidos da amostra. A razão é operacional: não há como
distinguir monorepos de forma sistemática e automática apenas pela API do
GitHub. O `google-cloud-node` — caso que gerou o erro 422 da issue #56 — foi
resolvido com a codificação de tags na URL do `compare`; o repositório permanece
na amostra mas suas tags com barra (`/`) e `#` são tratadas corretamente.

Caso análise posterior identifique outros monorepos com alta frequência de
tags, eles deverão ser excluídos na seção de ameaças à validade.

### Lead time por tag — combinação C3 da RQ 07

A terceira combinação operacional da RQ 07 usa **frequência por tag** como
proxy de deploy, mantendo o lead time (a) e o CFR (a) das combinações
anteriores. **Não há coleta nova**: as tags já estão em `tags.csv` e a
frequência é calculada diretamente a partir de `data_commit`. A coluna
`freq_tag` em `metricas.csv` registra esse valor.

Essa decisão foi tomada porque as tags cobrem projetos que marcam versões sem
criar releases formais no GitHub, ampliando a cobertura da RQ 07 sem custo
adicional de API.

---

## Rework rate (RQ 08a — bônus)

O rework rate é a proporção de releases corretivas sobre o total avaliado, sem
o limite de 7 dias do CFR(b):

```
rework_rate = corretivas / avaliadas
```

A variante `rework_rate_7d` restringe o numerador às corretivas publicadas em
até 7 dias da release anterior, tornando-a comparável ao CFR(b). A diferença
entre as duas versões indica a proporção de correções tardias que o CFR(b) não
captura.
