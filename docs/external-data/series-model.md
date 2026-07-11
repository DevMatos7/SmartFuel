# Modelo de séries externas

Séries iniciais do catálogo:

| Código | Frequência | Unidade | Moeda |
|--------|------------|---------|-------|
| BRENT_CRUDE_OIL | DAILY | USD_PER_BARREL | USD |
| USD_BRL_REFERENCE | DAILY | BRL_PER_USD | BRL |
| CEPEA_ETHANOL_MT | WEEKLY | BRL_PER_LITER | BRL |
| CSONLINE_PRICE_INFORMATION | IRREGULAR | INDEX_POINTS | — |

Bootstrap: `POST /api/v1/external-data/bootstrap-catalog`

Cada série possui `source_unit`, `canonical_unit`, `conversion_policy`, calendário e grace de freshness.
