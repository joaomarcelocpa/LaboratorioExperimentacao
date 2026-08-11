# Lab01 — Conexão com a API do GitHub e Script de Extração (Sprint 1, parte inicial)

## Contexto

Sprint 1 do Lab01 (Repositórios Populares + Kanban) pede um script que busca os 100
repositórios mais estrelados do GitHub com 9 campos mapeados para as RQs do trabalho.
O grupo (João, Bernardo e Miguel) dividiu a sprint entre os integrantes; este documento
cobre apenas a parte de **conexão com a API GraphQL do GitHub e o script de extração**.
Gravação em CSV, validação manual da amostra e o commit final da Sprint 1 ficam fora
deste escopo — são trabalho de outra parte do grupo.

Sem paginação: a Sprint 1 pede exatamente 100 repositórios, que cabem em uma única
chamada `first: 100`. Paginação com cursor é assunto da Sprint 2 (1.000 repositórios).

## Arquivos afetados

- `Laboratorio1/scripts/coleta.py` — script de extração
- `Laboratorio1/scripts/requirements.txt` — dependências (`requests`, `python-dotenv`)
- `.env.example` (raiz do repo) — documenta a variável `GITHUB_TOKEN`, sem valor real
- `.gitignore` (raiz do repo) — adiciona `.env`

## Autenticação

O token do GitHub (escopos `repo` e `read:project`, conforme o planejamento) é lido de
uma variável de ambiente `GITHUB_TOKEN`, carregada de um arquivo `.env` local via
`python-dotenv`. O `.env` nunca é commitado — só o `.env.example` com o nome da
variável. Se `GITHUB_TOKEN` não estiver definida, o script falha imediatamente com uma
mensagem clara, em vez de tentar seguir sem autenticação.

## Query GraphQL

Uma única query usando `search`, tipo `REPOSITORY`, ordenada por estrelas:

```graphql
query ($queryString: String!, $count: Int!) {
  search(query: $queryString, type: REPOSITORY, first: $count) {
    nodes {
      ... on Repository {
        name
        stargazerCount
        createdAt
        pushedAt
        primaryLanguage { name }
        pullRequests(states: MERGED) { totalCount }
        releases { totalCount }
        issues { totalCount }
        issuesClosed: issues(states: CLOSED) { totalCount }
      }
    }
  }
}
```

Mapeamento dos 9 campos para as RQs (conforme o planejamento):

| Campo GraphQL | Uso |
|---|---|
| `name` | identificação |
| `stargazerCount` | critério de seleção (top 100) |
| `createdAt` | RQ01 (idade) |
| `pushedAt` | RQ04 (tempo desde última atualização) |
| `primaryLanguage.name` | RQ05, RQ07 |
| `pullRequests(states: MERGED).totalCount` | RQ02 |
| `releases.totalCount` | RQ03 |
| `issues.totalCount` | RQ06 (denominador) |
| `issuesClosed.totalCount` (issues states: CLOSED) | RQ06 (numerador) |

`queryString` fixo: `"stars:>1 sort:stars-desc"`. `count` fixo em 100.

## Estrutura do script

`Laboratorio1/scripts/coleta.py`:

- Carrega `.env` e lê `GITHUB_TOKEN` no import do módulo; levanta `RuntimeError` com
  mensagem explicativa se a variável não existir.
- `fetch_top_repositories(count: int = 100) -> list[dict]`:
  - Monta o payload (`query` + `variables`) e faz `requests.post` para
    `https://api.github.com/graphql` com header `Authorization: Bearer <token>`.
  - Valida `response.status_code == 200`; caso contrário, levanta erro com o corpo da
    resposta para diagnóstico.
  - Valida ausência da chave `"errors"` no JSON de resposta (a API do GitHub pode
    retornar HTTP 200 com erros dentro do corpo); se presente, levanta erro com a
    mensagem retornada pela API.
  - Extrai e achata cada nó de `data.search.nodes` num dict simples com os 9 campos
    (ex.: `primaryLanguage.name` vira `linguagem`, tratando `None` quando o repositório
    não tem linguagem primária).
  - Retorna a lista de dicts — pensada para ser importada por quem for gravar o CSV
    depois.
- Bloco `if __name__ == "__main__":` chama `fetch_top_repositories(100)` e imprime cada
  repositório formatado no console (uma linha por repositório, campos separados), só
  para conferência visual. Nada é persistido em arquivo.

## Erros tratados (e o que fica de fora)

Tratados: token ausente, erro HTTP na requisição, erro reportado dentro do JSON do
GraphQL, linguagem primária ausente (`None`).

Fora do escopo, propositalmente: retry/backoff (só relevante na escala de 1.000
repositórios da Sprint 2), paginação, rate-limit handling além do erro básico, e
qualquer gravação em disco.

## Teste manual

Rodar `python coleta.py` com um `GITHUB_TOKEN` válido e confirmar visualmente que:
- 100 repositórios são retornados;
- os campos aparecem preenchidos (com `None` apenas onde não há linguagem primária);
- os primeiros da lista são de fato os mais estrelados no momento (checagem cruzada
  rápida com o GitHub Explorer).

A validação formal contra o site (5–10 repositórios, conferindo releases/linguagem/
issues) é passo 6 do roteiro da Sprint 1 e fica com a parte do CSV, fora deste escopo.
