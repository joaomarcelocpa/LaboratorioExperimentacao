# Plano da Sprint 2, explicado de forma simples (arquivo temporário)

A divisão segue o enunciado: **João = A, Bernardo = B, Miguel = C**.

## Em uma frase
Na Sprint 1 provamos que o programa funciona com 100 repositórios. Na Sprint 2 vamos (1) rodar para 300, (2) conferir à mão se a nossa regra de "release corretiva" acerta e (3) escrever a parte do artigo que explica como fizemos tudo.

## O que o professor pede nesta sprint
1. **300 repositórios** ou mais, depois dos filtros.
2. Todas as métricas calculadas, **inclusive as variantes** (as versões alternativas de cada métrica).
3. **Um arquivo CSV final** com uma explicação de cada coluna (o dicionário de dados).
4. **Conferência manual:** 60 repositórios avaliados por nós três, para ver se a nossa regra de "release corretiva" acerta.
5. **Artigo: seção de Metodologia** (como fizemos).

**Regra de nota:** cada pessoa precisa ter pelo menos uma issue com código commitado. Sem isso, a nota individual da sprint zera. Todo commit deve citar o número da issue.

---

## Tarefas por pessoa, ligadas ao que já foi feito na Sprint 1

### João

| Tarefa da Sprint 2 | O que é, em palavras simples | Ligação com a Sprint 1 |
|---|---|---|
| **Sorteio dos 60 repositórios e planilha** | Escolher 60 repositórios ao acaso (com seed, para dar o mesmo resultado sempre) e montar uma planilha com o link de cada release. A planilha **não** mostra o que o código achou. | Os 60 saem do conjunto final. O sorteio com seed usa a mesma ideia que você já usou na seleção dos 100. |
| **Calcular a concordância entre nós três** | Um script que lê os 3 arquivos de respostas e diz o quanto concordamos (a nota se chama kappa de Fleiss). Depois junta as respostas numa resposta final. | É código novo, mas lê o `repos.csv` e o `releases.csv` que você e o Bernardo geraram. |
| **Regra de desempate** | Escrever o que fazemos quando os três discordam (ex.: vale a maioria; se cada um disse uma coisa, decidimos em reunião). | Novo. |
| **Reposição de repositório** | Definir o que acontece quando um repositório dá erro e a amostra fica com 99. | Veio do `google-cloud-node`, que falhou na rodada de 100. |
| **Ampliar os labels de bug** | Incluir mais nomes de rótulo de bug para menos repositórios ficarem sem `cfr_c`. | Hoje 28 dos 99 não têm `cfr_c`. O código está em `coleta/issues.py`. |
| **Decidir o `cfr_c`** | Manter "bug aberto em até 7 dias" ou exigir que a issue cite a tag da release. | O código já tem os dois modos. Hoje usa o primeiro. |
| **Escrever a Metodologia (sua parte)** | Como escolhemos os repositórios, o funil e os fatores (estrelas, linguagem etc.). | Usa o `funil.csv`, o `descartes.csv` e o `repos.csv` da Sprint 1. |

### Bernardo

| Tarefa da Sprint 2 | O que é, em palavras simples | Ligação com a Sprint 1 |
|---|---|---|
| **Melhorar a regra de "release corretiva"** | Comparar o que a regra marcou com o que nós três respondemos. Medir acertos (precisão, recall e F1). Se o F1 ficar abaixo de 0,70, ajustar e medir de novo, anotando cada versão. | A regra atual está em `metricas/corretiva.py`. Hoje ela marca coisa demais: o `cfr_b` está em 43% e o rework rate vale 1,0 em 50 dos 99 repositórios. |
| **Decidir o que fazer com monorepos** | Um monorepo tem vários pacotes com tags separadas, e isso bagunça a ordem das releases. Opções: tirar da amostra, tratar por pacote ou só avisar no artigo. | O `google-cloud-node` falhou por isso (erro 422 no `compare`). |
| **Conferir o lead time por tag** | A pergunta 7 do enunciado usa a tag como "entrega". Precisa ver se já existe lead time por tag. Se não existir, criar com testes, ou trocar as combinações por outras que os dados já permitem. | Hoje só existe a frequência por tag (`freq_tag`). Os commits só foram coletados entre releases. |
| **Escrever a Metodologia (sua parte)** | O que é "entrega", lead time (a) e (b), CFR (a) e (b), release corretiva e as variantes. | Usa tudo o que você fez: `releases.py`, `commits.py`, `lead_time.py`, `corretiva.py`. |

### Miguel

| Tarefa da Sprint 2 | O que é, em palavras simples | Ligação com a Sprint 1 |
|---|---|---|
| **Rodar a coleta para 300** | Rodar o programa até completar 300 repositórios, com `--limite 300`. | O programa já existe. Na rodada de 100 levou 3h33. Para os 200 novos, a estimativa é ~8 h (~2,7 h cada, dividindo em 3 tokens). |
| **Tamanho do `commits.csv`** | O arquivo já tem 54 MB e deve passar de 100 MB. O GitHub recusa arquivos desse tamanho. Escolher: Git LFS, arquivo compactado (`.csv.gz`) ou só commitar nos marcos. | Veio da coleta de commits do Bernardo. |
| **Execuções de CI que ficaram de fora** | Em 31 intervalos de tempo a API cortou os dados (24 no `pytorch`). Ver se dá para pegar mais ou registrar como limitação. | Está no `fatias_saturadas.csv`, gerado pelo `coleta/runs.py` dele. |
| **Dataset final e dicionário de dados** | Juntar tudo no CSV final e explicar cada coluna (nome, tipo, unidade, de onde vem). | Já existe um `docs/dicionario_dados.md` e uma validação dos CSVs. É preciso atualizar com o que for novo. |
| **Escrever a Metodologia (sua parte)** | Como o programa coleta: cache, limite da API, tentativas em caso de erro, custo e tempo. | Usa `coleta/http.py`, `cache.py`, `custo_api.csv` e a estimativa de custo. |

### Os três juntos

| Tarefa | O que é | Ligação com a Sprint 1 |
|---|---|---|
| **Responder a planilha dos 60, cada um sozinho** | Para cada repositório: qual o tipo (biblioteca, aplicação, ferramenta de linha de comando)? As releases são entregas de verdade? Para 5 releases sorteadas, ela é corretiva? Ninguém vê a resposta do outro nem o que o código achou. Cada um commita o seu arquivo. | As releases e os commits vêm de `releases.csv` e `commits.csv`. O "tipo do projeto" é o fator que faltou na pergunta 6. |
| **Reunião para combinar as respostas** | Discutir só os casos em que discordamos e fechar uma resposta final. | Novo. |
| **Hipóteses que faltam** | Miguel já avisou que vai subir as da 03a, 04, 05 e 08b. | Continuação da Sprint 1. |

---

## Ordem sugerida (uma coisa depende da outra)

1. **Decidir primeiro:** monorepos (Bernardo), reposição e labels de bug (João), formato do `commits.csv` (Miguel).
2. **Rodar os 300** (Miguel), já com essas decisões.
3. **Sortear os 60 e gerar a planilha** (João), depois que os 300 fecham.
4. **Responder a planilha**, os três ao mesmo tempo, sem trocar informação.
5. **Calcular a concordância e juntar as respostas** (João).
6. **Medir e ajustar a regra de release corretiva** (Bernardo).
7. **Recalcular as métricas com a regra nova** e fechar o dataset e o dicionário (Miguel).
8. **Escrever a Metodologia** (cada um a sua parte, os três revisam).

## O que dá para adiantar antes dos 300 ficarem prontos
- Script do sorteio dos 60 e da planilha (João).
- Script de concordância, testado com respostas inventadas (João).
- Script que mede precisão, recall e F1, com testes (Bernardo).
- Conferir se existe lead time por tag (Bernardo).
- Escolher e testar o formato compacto do `commits.csv` (Miguel).

## Duas perguntas para combinar com o grupo
1. Os 300 usam a mesma seed (os 100 de agora continuam dentro) ou é um sorteio novo? Com a mesma seed o cache evita refazer os 100 primeiros.
2. O "tipo do projeto" só será respondido para os 60 da conferência. Para a pergunta 6 isso dá poucos repositórios por grupo. Vale decidir se o grupo aceita isso ou se rotula mais.
