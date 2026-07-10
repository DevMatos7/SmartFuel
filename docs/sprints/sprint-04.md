# Sprint 4 — Motor de comparação de cotações

## Entregas

- Parâmetros financeiros por organização (`financial_parameters`)
- Execuções e resultados de comparação (`quote_comparison_runs`, `quote_comparison_results`)
- Motor de candidatos históricos (`activated_at <= comparison_datetime`)
- Elegibilidade estruturada com motivos bloqueantes e alertas
- Custo entregue e custo equivalente à vista (Decimal)
- Ranking RAW / DELIVERED / FINANCIAL_EQUIVALENT
- Escopo BEST_PER_DISTRIBUTOR / ALL_OFFERS
- Spread, média e diferença para a melhor oferta
- Snapshots imutáveis com hash SHA-256
- Exportação PDF e CSV
- Telas: comparar, histórico, detalhes, parâmetros financeiros

## Metodologia

Versão: `QUOTE_COMPARISON_V1`

- Taxa diária: `(1 + taxa_anual) ^ (1/365) - 1`
- Custo entregue: `preço - desconto - bonificação + frete + outros`
- Equivalente à vista: `entregue / (1 + taxa_diária) ^ dias_financeiros`

## Migration

`0007_sprint4_comparisons`
