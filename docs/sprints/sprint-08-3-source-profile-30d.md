# Sprint 8.3 — Perfil de fontes de itens (30 dias)

Filial `2443` · `2026-06-12` → `2026-07-11`

## Totais

| Métrica | ITENSMOVPRODUTOS | ITENSCOMPROVANTE |
|---------|------------------|------------------|
| Notas com itens | 25 | 93 |
| Total de itens | 28 | 168 |
| Volume LT (todas unidades L*) | 115000.0 | 115000.0 |
| Volume LT combustível (1/2/4/1271/1272) | 115000.0 | 115000.0 |
| Valor itens | 619550.5524 | 623521.6900 |

Notas totais: **93**
Somente movimento: **0** · Somente fiscal: **68** · Ambas: **25** · Nenhuma: **0**

## Dias candidatos (combustível LT no movimento)

| Dia | Notas | Linhas | Volume LT | Custo ~ |
|-----|-------|--------|-----------|---------|
| 2026-06-16 | 3 | 3 | 20000.000 | 114915.8281 |
| 2026-06-17 | 3 | 3 | 15000.000 | 80911.8301 |
| 2026-06-20 | 2 | 2 | 10000.000 | 32579.1699 |
| 2026-06-23 | 4 | 4 | 20000.000 | 112358.6992 |
| 2026-06-24 | 2 | 2 | 10000.000 | 64647.4004 |
| 2026-06-26 | 2 | 2 | 15000.000 | 81946.7471 |
| 2026-07-02 | 4 | 4 | 25000.000 | 125100.1387 |

**Dia recomendado (menor primeiro na lista):** `2026-06-20`

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

