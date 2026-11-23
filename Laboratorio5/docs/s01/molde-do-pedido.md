# Molde do pedido (congelado)

Todos os pedidos P1 a P4 usam este molde, com redação congelada. Nenhuma seção pode ser alterada
após o início da coleta. Não há dicas de solução nem referência à estrutura interna do código.

---

```
[CONTEXTO] O projeto está no diretório atual.

[NECESSIDADE] <O que o negócio precisa — 1 a 3 frases.>

[COMPORTAMENTO PARA O USUÁRIO] <O que o usuário faz e vê.>

[CRITÉRIOS DE ACEITAÇÃO]
- <Critério 1 — observável, com número quando couber.>
- <Critério 2>
- ...

[SAÍDA] Implemente a mudança no próprio projeto. O resultado será verificado por testes
automatizados de comportamento.
```

---

## Regras de redação

- Cada seção é obrigatória.
- `[NECESSIDADE]` descreve o problema de negócio, sem mencionar rotas, tabelas ou classes.
- `[COMPORTAMENTO PARA O USUÁRIO]` descreve o que o usuário faz e vê na interface ou via API,
  sem mencionar camadas internas.
- `[CRITÉRIOS DE ACEITAÇÃO]` são observáveis por testes caixa-preta: números, tempos e
  respostas HTTP. Para pedidos que tensionam a arquitetura (P3), incluir o mínimo observável
  (cabeçalho HTTP, atributos `data-testid`) como parte do comportamento.
- `[SAÍDA]` é idêntica em todos os pedidos.
- Proibido citar: nomes de pacotes, classes, tabelas, índices, colunas internas, padrões de
  projeto ou dicas de como implementar.
