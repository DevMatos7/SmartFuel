# Aging — contas a pagar

Faixas:

| Bucket | Critério |
|--------|----------|
| OVERDUE | due_date < hoje e open_amount > 0 |
| 0_7 | 0–7 dias |
| 8_15 | 8–15 |
| 16_30 | 16–30 |
| 31_60 | 31–60 |
| OVER_60 | > 60 |

## Prazo médio ponderado

`Σ(amount × days) / Σ(amount)`

Base padrão: `ENTRY_DATE` (fallback `ISSUE_DATE` quando entry ausente no título).

Implementação: `backend/app/core/accounts_payable.py`.
