# Bases de custo

| Tipo | Descrição |
|------|-----------|
| `LAST_CONFIRMED_PURCHASE` | Última compra válida antes de T |
| `WEIGHTED_PURCHASE_COST` | Média ponderada por volume na janela |
| `BEST_CURRENT_ELIGIBLE_QUOTE` | Melhor cotação elegível (motor Sprint 4) |
| `AVERAGE_ELIGIBLE_QUOTE` | Média das cotações elegíveis |
| `CONSERVATIVE_MAX` | `max(compra, reposição)` |
| `MANUAL_APPROVED_COST` | Override auditado com validade |
| `SYNTHETIC_COST` | Homologação sintética |

Cada resolução persiste: tipo, valor, datetime, `available_at`, idade, confiança (`HIGH|MEDIUM|LOW|UNAVAILABLE`) e warnings.

Custo desconhecido → `UNAVAILABLE` / `MISSING_COST`. Nunca assume 0.
