# Revisões de observações

Nunca sobrescrever silenciosamente.

| Hash | Resultado |
|------|-----------|
| Igual | `SKIPPED_UNCHANGED` |
| Diferente no mesmo período | `NEW_REVISION` |

Estados: `CURRENT`, `SUPERSEDED`, `REJECTED`, `MANUAL_REVIEW`.

Chave lógica: `series_id + observation_datetime + revision_number`.
