# Sprint 8.2 — Cobertura XPERT × PostgreSQL

Posto: `1edc5c8b-0ba1-405c-a000-03e61e31521e` · Filial ERP `2443`

## Cobertura efetivamente carregada no PG (todas as datas)

| Métrica | Valor |
|---------|-------|
| Primeiro dia de compra no PG | 2026-07-08 |
| Último dia de compra no PG | 2026-07-09 |
| Dias com compras no PG | 2 |
| Notas no PG | 4 |
| Itens no PG | 2 |
| Cotações ativadas no posto | 0 |

## Janelas pesquisadas vs origem

### 1 dia(s) — pesquisado `2026-07-11` → `2026-07-11`

| Métrica | XPERT | PostgreSQL |
|---------|-------|------------|
| Notas | 0 | 0 |
| Itens | 0 | 0 |
| Dias com compra | 0 | 0 |
| Primeiro dia na janela | None | None |
| Último dia na janela | None | None |
| Itens mapeados | — | 0 |
| Itens volume>0 | — | 0 |

Gap notas: **0** · Gap itens: **0**

_Contagens alinhadas ou PG >= XPERT na janela._

Unidades XPERT: `{}`
Unidades PG: `{}`

### 7 dia(s) — pesquisado `2026-07-05` → `2026-07-11`

| Métrica | XPERT | PostgreSQL |
|---------|-------|------------|
| Notas | 11 | 4 |
| Itens | 2 | 2 |
| Dias com compra | 6 | 2 |
| Primeiro dia na janela | 2026-07-05 | 2026-07-08 |
| Último dia na janela | 2026-07-10 | 2026-07-09 |
| Itens mapeados | — | 0 |
| Itens volume>0 | — | 0 |

Gap notas: **7** · Gap itens: **0**

_PG cobre apenas o subconjunto sincronizado; janela pesquisada ≠ cobertura carregada._

Unidades XPERT: `{'UN': 2}`
Unidades PG: `{'UN': 2}`

### 30 dia(s) — pesquisado `2026-06-12` → `2026-07-11`

| Métrica | XPERT | PostgreSQL |
|---------|-------|------------|
| Notas | 93 | 4 |
| Itens | 28 | 2 |
| Dias com compra | 29 | 2 |
| Primeiro dia na janela | 2026-06-12 | 2026-07-08 |
| Último dia na janela | 2026-07-10 | 2026-07-09 |
| Itens mapeados | — | 0 |
| Itens volume>0 | — | 0 |

Gap notas: **89** · Gap itens: **26**

_PG cobre apenas o subconjunto sincronizado; janela pesquisada ≠ cobertura carregada._

Unidades XPERT: `{'LT': 20, 'UN': 7, 'KG': 1}`
Unidades PG: `{'UN': 2}`

## Interpretação formal

- `compras comparáveis nos dados disponíveis no PG = 0`
- **não** afirmar ainda: `compras comparáveis no XPERT em 90 dias = 0`
- Agenda XPERT permanece bloqueada; expansões de carga são manuais.

## Produtos 1505 / 1506

| ERP ID | Nome | Unidade | NCM |
|--------|------|---------|-----|
| 1505 | ADITIVO FLEX 200ML BARDAHL | UN | 38119090 |
| 1506 | FLUIDO PARA RADIADOR ROSA 1L BARDAHL | UN | 38249941 |

Movimentos 90d no XPERT: **2**

Ver `sprint-08-2-product-diag.json` para itens PG e exclusões.

## Combustível a granel no XPERT (30d) — ainda fora do PG

| ERP ID | Nome | Unidade | Mov. | Qtde (LT) |
|--------|------|---------|------|-----------|
| 4 | DIESEL S10 COMUM | LT | 6 | 40000 |
| 1 | ETANOL COMUM | LT | 6 | 35000 |
| 2 | GASOLINA COMUM | LT | 6 | 30000 |
| 1272 | ETANOL ADITIVADO | LT | 1 | 5000 |
| 1271 | GASOLINA ADITIVADA | LT | 1 | 5000 |

**Não mapear 1505/1506 como combustível.** Preferir `IGNORED` (aditivo / fluido de loja).

Próximo passo operacional: sync manual 7 dias → reconciliar → mapear IDs acima → só então nova descoberta.

