# Spread e média

## Conjunto utilizado

Média e spread consideram apenas ofertas com `rank_position` preenchido — ou seja, o conjunto efetivo do ranking atual.

Em `BEST_PER_DISTRIBUTOR`, cada distribuidora contribui uma vez. Em `ALL_OFFERS`, cada condição elegível contribui.

## Fórmulas

```
média = soma(custos_ranking) / quantidade

spread_absoluto = maior_custo - menor_custo

spread_percentual = spread_absoluto / menor_custo × 100
```

Spread percentual só é calculado com duas ou mais ofertas no conjunto.

## Precisão

Cálculos com `Decimal` e `ROUND_HALF_UP`.
