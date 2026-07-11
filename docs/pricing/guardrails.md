# Guardrails e arredondamento

## Guardrails

Limites absolutos e percentuais de alta/queda. Mudança abaixo do mínimo → `HOLD`.

Persistir sempre:

- `raw_recommended_price`
- `guarded_recommended_price`
- `guardrail_applied`
- `guardrail_reason`

Não truncar silenciosamente sem registrar o original.

## Arredondamento

`NONE | NEAREST_CENT | END_WITH_9 | END_WITH_99 | CUSTOM_INCREMENT`

O arredondamento **nunca** reduz o preço abaixo do piso comercial.
