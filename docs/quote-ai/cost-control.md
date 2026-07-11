# Controle de custo

## Limites no provider config

- `daily_cost_limit`
- `monthly_cost_limit`
- `per_document_cost_limit`

Mock: `provider_cost=0` (homologação sem gasto).

## Telemetria por extração

`input_tokens`, `output_tokens`, `provider_cost`, `cost_currency` em `quote_ai_extractions`.

## Alertas

| Código | Uso |
|--------|-----|
| `QUOTE_AI_BUDGET_EXCEEDED` | Estouro de limite |
| `QUOTE_AI_COST_SPIKE` | Pico anômalo de custo |

Permissão `quote_ingestion.view_costs` para visualizar custos.

Provedor externo só com flag `quote_ai_provider_enabled` e secret homologado.
