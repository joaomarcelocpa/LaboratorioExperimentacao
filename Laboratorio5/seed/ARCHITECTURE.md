# Arquitetura da semente

Gerenciador de tarefas em arquitetura hexagonal (portas e adaptadores). Pacote base: `labexp.semente`.

## Pacotes

```
labexp.semente
├── domain                     Tarefa, StatusTarefa, TarefaInvalidaException
├── application
│   ├── port.in                casos de uso (CriarTarefa, ListarTarefas, ConsultarTarefa,
│   │                          AtualizarTarefa, ConcluirTarefa, ExcluirTarefa), DadosTarefa,
│   │                          TarefaNaoEncontradaException
│   ├── port.out               TarefaRepositorio
│   └── service                TarefaService (implementa as portas de entrada)
├── adapter
│   ├── in.web                 TarefaController, TarefaRequest, TarefaResponse, TratadorDeErros
│   └── out.persistence        TarefaEntity, TarefaJpaRepository, TarefaRepositorioJpa
└── config                     Application, Montagem
```

## Papel de cada pacote

- **domain**: regras e invariantes da tarefa. Não conhece mais nada.
- **application**: casos de uso e as portas que eles usam. Depende só de `domain`.
- **adapter.in.web**: traduz HTTP para as portas de entrada. Só conhece `application.port.in`.
- **adapter.out.persistence**: implementa `TarefaRepositorio` com JPA/PostgreSQL.
- **config**: único pacote que conhece todos os outros; monta os casos de uso e inicia a aplicação.

## Direção das dependências

`adapter.in.web` → `application.port.in` ← `application.service` → `application.port.out` ← `adapter.out.persistence`;
tudo aponta para `domain`. `config` aponta para todos.

## Regras verificáveis

Cada regra é um teste em `src/test/java/labexp/semente/ArquiteturaTest.java`.

1. `domainNaoDependeDeNada`: `domain` não depende de `application`, de adaptadores, de `config`, de Spring nem de JPA.
2. `applicationDependeSoDeDomain`: `application` depende só de `domain` e do JDK.
3. `entradaESaidaIndependentes`: `adapter.in` não depende de `adapter.out`, e vice-versa.
4. `semCiclosEntrePacotes`: não há ciclos entre os pacotes de primeiro nível nem entre `adapter.in` e `adapter.out`.
5. `controladoresNaoAcessamRepositorios`: classes de `adapter.in.web` não dependem de `application.port.out`, de Spring Data nem de `adapter.out`.

## Fora do escopo desta arquitetura

Não existem, de propósito: filtros, paginação, noção de empresa ou usuário, agendamento, importação de arquivos.
