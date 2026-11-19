# Contrato de execução da semente

Este contrato é igual em todas as cadeias do experimento e está fora do controle do agente. Os testes dependem dele; mudá-lo invalida a comparação entre cadeias.

| Item | Contrato |
|---|---|
| Subir | `docker compose up` (em `seed/`) sobe a aplicação e o PostgreSQL |
| Porta | A aplicação escuta em `8080` |
| Prontidão | `GET /health` responde `200` quando a aplicação está pronta e o banco responde |
| Banco | Configurado **somente** pela variável de ambiente `DATABASE_URL` (URL JDBC com `user` e `password`) |
| Dados de teste | Carregados só pelos endpoints existentes da semente, em paralelo |
| Acesso ao banco | Os testes nunca acessam o banco diretamente |
| Esquema | Criado pela própria aplicação na subida (migração Flyway) |

## Exemplo

```
docker compose up -d --build
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health   # 200
```

## O que a semente garante ao agente e aos testes

- `GET /health` só vira `200` depois da migração do esquema e com o banco acessível.
- Toda interface exposta aos testes usa `data-testid` (lista em `seed/ARCHITECTURE.md` e `semente.md`).
- Não há outra configuração por variável de ambiente além de `DATABASE_URL`.
