# Mapeamento de produtos ERP

## Chave lógica

`station_id + erp_product_id` — o mesmo ID pode existir em postos diferentes.

## Status

| Status | Significado |
|--------|-------------|
| PENDING | Aguardando revisão |
| MAPPED | Vinculado a produto canônico |
| IGNORED | Não é combustível (exige motivo) |
| CONFLICT | Inconsistência detectada |

## Regras

- MAPPED exige `canonical_product_id`, `mapped_by`, `mapped_at`
- IGNORED exige `ignore_reason`
- Remapeamento gera histórico em `product_mapping_history`
- Importação CSV atualiza apenas campos de origem; preserva mapeamentos manuais

## Endpoints

- `GET /api/v1/erp-products`
- `POST /api/v1/erp-products/{id}/map`
- `POST /api/v1/erp-products/bulk-map`
- `POST /api/v1/erp-products/{id}/ignore|reopen`
- `GET /api/v1/erp-products/{id}/history`
