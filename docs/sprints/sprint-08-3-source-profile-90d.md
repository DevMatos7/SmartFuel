# Sprint 8.3 — Perfil de fontes de itens (90 dias)

Filial `2443` · `2026-04-13` → `2026-07-11`

## Totais

| Métrica | ITENSMOVPRODUTOS | ITENSCOMPROVANTE |
|---------|------------------|------------------|
| Notas com itens | 86 | 274 |
| Total de itens | 92 | 505 |
| Volume LT (todas unidades L*) | 470000.0 | 470000.0 |
| Volume LT combustível (1/2/4/1271/1272) | 470000.0 | 470000.0 |
| Valor itens | 2533201.0910 | 2556878.6400 |

Notas totais: **274**
Somente movimento: **0** · Somente fiscal: **188** · Ambas: **86** · Nenhuma: **0**

## Dias candidatos (combustível LT no movimento)

| Dia | Notas | Linhas | Volume LT | Custo ~ |
|-----|-------|--------|-----------|---------|
| 2026-04-13 | 4 | 4 | 25000.000 | 127222.1484 |
| 2026-04-17 | 4 | 4 | 25000.000 | 150759.9902 |
| 2026-04-21 | 6 | 6 | 35000.000 | 189125.7734 |
| 2026-04-29 | 3 | 3 | 25000.000 | 133075.2539 |
| 2026-05-01 | 4 | 4 | 25000.000 | 144824.5410 |
| 2026-05-06 | 4 | 4 | 25000.000 | 117686.2109 |
| 2026-05-14 | 9 | 9 | 65000.000 | 357191.3223 |
| 2026-05-18 | 3 | 3 | 25000.000 | 144845.1289 |
| 2026-05-21 | 1 | 1 | 5000.000 | 30844.2598 |
| 2026-05-26 | 3 | 3 | 20000.000 | 100070.8711 |
| 2026-06-02 | 6 | 6 | 35000.000 | 197303.7051 |
| 2026-06-03 | 1 | 1 | 10000.000 | 32327.9902 |
| 2026-06-05 | 2 | 2 | 10000.000 | 49967.1523 |
| 2026-06-09 | 5 | 5 | 25000.000 | 129075.0215 |
| 2026-06-16 | 3 | 3 | 20000.000 | 114915.8281 |
| 2026-06-17 | 3 | 3 | 15000.000 | 80911.8301 |
| 2026-06-20 | 2 | 2 | 10000.000 | 32579.1699 |
| 2026-06-23 | 4 | 4 | 20000.000 | 112358.6992 |
| 2026-06-24 | 2 | 2 | 10000.000 | 64647.4004 |
| 2026-06-26 | 2 | 2 | 15000.000 | 81946.7471 |
| 2026-07-02 | 4 | 4 | 25000.000 | 125100.1387 |

**Dia recomendado (menor primeiro na lista):** `2026-05-21`

## Mapa de colunas ITENSCOMPROVANTE

```json
{
  "id": "ID_ITENSCOMPROVANTE",
  "invoice": "ID_COMPROVANTE",
  "product": "ID_PRODUTOS",
  "qty": "QTDE",
  "unit_price": "VLRUNITARIO",
  "total": "VLRTOTALITEM",
  "filial": "ID_FILIAL",
  "db": "ID_DB",
  "desc": null,
  "cfop": "CFOP",
  "ncm": null,
  "discount": "VLRDESCONTO",
  "seq": "DFE_NITEM",
  "cost": "VLRCUSTO",
  "freight": "VLRFRETE",
  "insurance": "VLRSEGURO",
  "other": "VLROUTROS",
  "icms": "VLRICMSITEM",
  "icms_st": "VLRSUBSTITEM",
  "fcp": "VALOR_FECOP"
}
```

