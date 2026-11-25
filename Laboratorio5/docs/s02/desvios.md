# Registro de desvios de protocolo

**Regra:** qualquer mudança feita após a criação da tag `protocolo-v1` em pedidos, testes,
versão do modelo ou do Claude Code é um desvio e deve ser registrado aqui imediatamente.
Dados coletados antes e depois de um desvio são analisados separadamente ou os afetados
são descartados, conforme decisão do grupo.

---

## Desvios registrados

_Nenhum desvio até o momento._

---

## Formato de cada desvio

```
### D<n> — <título curto>

**Data:** YYYY-MM-DD
**Descoberto por:** @membro
**Passo afetado:** passo X da cadeia Y (ou "antes da coleta")
**Descrição:** o que mudou e por quê.
**Impacto estimado:** quais cadeias ou passos foram afetados.
**Decisão:** descartar / analisar separadamente / sem impacto (justificar).
**Aprovado por:** @A, @B, @C
```
