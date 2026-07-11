# Matching de entidades

Após a extração, `QuoteIngestionPipelineService._match_entities` sugere vínculos com cadastros existentes.

## Tipos

`DISTRIBUTOR` · `PRODUCT` · (`BASE`, `STATION`, `PAYMENT_CONDITION` previstos no enum)

## Status

| Status | Significado |
|--------|-------------|
| `MATCHED` | Um candidato claro |
| `SUGGESTED` | Candidato parcial |
| `AMBIGUOUS` | Múltiplos candidatos → sem ID definitivo |
| `NOT_FOUND` | Sem cadastro correspondente |

## Métodos

- Distribuidora: similaridade de nome (`NAME_SIMILARITY` / `NAME_EXACT_OR_SIMILAR`)
- Produto: nome/código + aliases (S10, etanol, gasolina, S500)

## Proibições

- **Não** cria distribuidora, produto, posto ou condição de pagamento
- Rascunho exige `distributor_id` e `station_id` confirmados (`ENTITY_CONFIRMATION_REQUIRED`)
- Binding de produtos pode ser enviado em `product_bindings` no create-draft
