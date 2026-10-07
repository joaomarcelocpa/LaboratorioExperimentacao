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
