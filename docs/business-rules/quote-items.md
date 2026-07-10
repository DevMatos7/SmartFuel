# Itens de cotação

## Modelo

Cada item representa uma condição comercial para um produto canônico ativo e comprável (RDC-004).

Valores monetários: `NUMERIC` / `Decimal` — nunca `float` (RDC-019, RNF-001).

| Campo | Tipo | Regra |
|-------|------|-------|
| `quoted_price_per_liter` | NUMERIC(14,4) | > 0 |
| `minimum_volume_liters` | NUMERIC(16,3) | > 0 |
| `available_volume_liters` | NUMERIC(16,3) | ≥ 0; alerta se < mínimo |
| `discount_per_liter` | NUMERIC(14,4) | ≥ 0 |
| `rebate_per_liter` | NUMERIC(14,4) | ≥ 0 (bonificação) |
| `other_cost_per_liter` | NUMERIC(14,4) | > 0 exige descrição |

## Snapshot da condição de pagamento (RDC-005)

Ao incluir item, o sistema grava:

- `payment_type_snapshot`
- `payment_term_days_snapshot`
- `payment_term_name_snapshot`

Alterações futuras no cadastro de condições **não** retroagem.

## Múltiplas condições por produto (RDC-022)

Permitido quando diferem em condição, frete, preço, prazo, base, validade ou volume.

## Duplicidade exata (RDC-023)

Bloqueada na mesma cotação quando coincidem: produto, condição, preço, frete e validade. Erro: `DUPLICATE_QUOTE_ITEM`.

## Frete (RDC-024, RDC-025)

- `freight_type`: `CIF` ou `FOB`
- `freight_calculation_type`: `NONE`, `TOTAL`, `PER_LITER`
- Não informar valores conflitantes entre total e por litro

## Base (RDC-029)

Base do cabeçalho pode ser nula. Item pode sobrescrever; deve pertencer à distribuidora.

## Pré-preenchimento (RF-017)

`GET /api/v1/quotes/item-prefill?station_id=&distributor_id=&product_id=` consulta regra comercial efetiva e sugere volume mínimo e alertas. Valores persistidos são snapshot no item (RDC-021).

## Endpoints

- `POST /api/v1/quotes/{id}/items`
- `PATCH /api/v1/quotes/{id}/items/{item_id}`
- `DELETE /api/v1/quotes/{id}/items/{item_id}` (somente `DRAFT`)

Todos os comandos de escrita exigem `expected_version` da cotação.
