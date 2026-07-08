# Condições de pagamento

## Tipos

| Tipo | Dias |
|------|------|
| CASH | 0 |
| TERM | > 0 |
| ANTICIPATED | 0 (nesta sprint) |

## Unicidade

`organization_id + payment_type + days + normalized_name`

## Endpoints

- `GET/POST /api/v1/payment-terms`
- `PATCH /api/v1/payment-terms/{id}`
- `POST /api/v1/payment-terms/{id}/deactivate|reactivate`

Permissão de escrita: `ADMIN` e `FINANCEIRO`.
