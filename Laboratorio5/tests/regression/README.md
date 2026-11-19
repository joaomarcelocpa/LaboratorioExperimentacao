# Testes de regressão da semente

Caixa-preta: falam com a aplicação só por HTTP e pela interface web (Playwright). Nunca acessam o banco.

## Rodar

1. Subir a semente: `docker compose up -d --build` em `Laboratorio5/seed`.
2. Rodar os testes (precisa de JDK 21, Maven e navegadores do Playwright):

```
mvn -q test
```

`BASE_URL` muda o endereço (padrão `http://localhost:8080`).

Sem JDK local, por container (o container enxerga a semente por `host.docker.internal`):

```
docker run --rm -v "<caminho>/tests/regression:/w" -w /w -e BASE_URL=http://host.docker.internal:8080 mcr.microsoft.com/playwright/java:v1.48.0-jammy mvn -B -q test
```

Cada teste usa um `responsavel` único e apaga o que criou pelos endpoints, então não há dependência de ordem nem de estado do banco.
