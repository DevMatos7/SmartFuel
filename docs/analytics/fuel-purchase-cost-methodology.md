# Metodologia — custo de compra de combustível

## Conceitos

| Conceito | Descrição |
|----------|-----------|
| ERP_RECORDED_COST | Valor informado pelo ERP (`source_total_cost` / unitário) |
| COMMERCIAL_DELIVERED_COST | Bruto − desconto − rebate + frete + seguro + outras despesas |
| ACCOUNTING_COST | Somente quando o ERP fornecer de forma confiável |

Tributos (ICMS, ICMS-ST, FCP, PIS, COFINS) são preservados separadamente e **não** reduzem o custo comercial automaticamente.

## Rateio de cabeçalho

Quando frete/despesas existem só no cabeçalho:

`allocation_method = PROPORTIONAL_GROSS_AMOUNT`

Resíduo no último item (ordem determinística). Valores já por item não são rateados de novo.

## Custo por litro

`delivered_cost_per_liter = commercial_delivered_cost / volume_liters` somente se `volume_liters > 0`.

Arredondamento: `ROUND_HALF_UP` (quantidades 6, custo/L 8, totais 4).

## Benchmark vs cotação (Sprint 8)

A comparação compra × cotação usa o mesmo `commercial_delivered_cost` como custo real e o motor de custo entregue das cotações (Sprint 4) como benchmark histórico. Ver [purchase-benchmark-methodology.md](./purchase-benchmark-methodology.md).
