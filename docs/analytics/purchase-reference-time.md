# Referência temporal da compra

## Fontes (precedência)

1. `PURCHASE_ORDER_DATETIME` (pedido — reservado)
2. `MANUAL_DECISION_DATETIME` (override auditado)
3. `INVOICE_ISSUE_DATETIME` (emissão)
4. `ENTRY_DATETIME_FALLBACK` (entrada)
5. `UNKNOWN`

## Confiança

| Fonte | Confiança |
|-------|-----------|
| Pedido / decisão manual | HIGH |
| Emissão | MEDIUM |
| Entrada | LOW |
| Desconhecida | UNAVAILABLE |

Compras com confiança LOW exibem aviso. Parâmetro `allow_low_confidence_reference` controla se entram no ranking.
