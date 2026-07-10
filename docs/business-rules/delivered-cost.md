# Custo entregue

## Fórmula

```
custo_entregue_por_litro =
  preço_cotado
  - desconto_por_litro
  - bonificação_por_litro
  + frete_por_litro
  + outros_custos_por_litro
```

## Frete por litro

| Tipo | Cálculo |
|------|---------|
| `NONE` | 0 |
| `PER_LITER` | valor informado por litro |
| `TOTAL` | `frete_total / volume_solicitado` |

O volume solicitado é sempre o denominador do frete total — nunca volume mínimo ou disponível.

## Precisão

- Tipo: `Decimal`
- Persistência por litro: 8 casas (`LITER_PERSIST_SCALE`)
- Totais: 4 casas (`TOTAL_PERSIST_SCALE`)
- Arredondamento: `ROUND_HALF_UP`

## Elegibilidade

Resultado `<= 0` gera motivo `INVALID_DELIVERED_COST`.
