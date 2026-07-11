# Sprint 8.2 — Etapa A: sync manual 7 dias + cotações de exemplo

**Janela:** 2026-07-03 → 2026-07-09 (inclusivo) · Filial **2443** · Posto Matriz  
**Modo:** histórico/manual · ADMIN · XPERT UNSAFE (`sa`) · Scheduler **bloqueado** · Checkpoint **não avançado**

---

## 0. Cotações de exemplo (antes do sync)

Criadas **6** cotações ativadas no posto Matriz (`activated_at = agora`, validade 7 dias).

| # | Produto | Distribuidora | Preço R$/L |
|---|---------|---------------|------------|
| 1–3 | Etanol / Gasolina C / Diesel S10 | DIST-EX-A | 3,89 / 5,79 / 5,45 |
| 4–6 | Etanol / Gasolina C / Diesel S10 | DIST-EX-B | 3,92 / 5,81 / 5,48 |

Artefato: `docs/sprints/sprint-08-2-example-quotes.json`

**Importante:** essas cotações **não** são evidência histórica de compras de 03–09/07. Servem para prontidão operacional futura. Homologação real de benchmark de compras **passadas** continua bloqueada se não houver cotação com `activated_at <= T` da compra.

---

## 1. Pré-voo

| Item | Resultado |
|------|-----------|
| Backup PG | `docs/sprints/backup_pre_sprint82_7d.dump` (~14,3 MB, custom) |
| Contratos | **VALID** nos 3 datasets |
| `query_hash` | stored = live (match) |
| `normalization_version` | `FUEL_PURCHASE_V1` |
| `hash_schema_version` | `1` |
| Scheduler | `schedule_enabled = false` |
| Overlap na janela | forçado a **0** durante o sync (restaurado a 86400 depois) |
| Checkpoint watermark | `null` — não usado / não avançado (`checkpoint_before = checkpoint_after = null`) |

### Contagens antes

| Dataset | XPERT | PG antes | Gap |
|---------|-------|----------|-----|
| Notas | **14** | 4 | 10 |
| Itens | **2** | 2 | 0 |
| Títulos | **19** | 6 | 13 |
| Volume LT (XPERT) | **0** | — | — |

> O probe anterior citava **11** notas: referia-se a outra janela (ex.: 7 dias móveis). Na janela autorizada **03–09/07**, o XPERT tem **14** notas. PG alinhou para 14.

---

## 2. Passagem 1 (ordem obrigatória)

| Dataset | read | inserted | updated | unchanged | errors |
|---------|------|----------|---------|-----------|--------|
| FUEL_PURCHASE_INVOICES | 14 | **10** | 0 | **4** | 0 |
| FUEL_PURCHASE_ITEMS | 2 | 0 | 0 | **2** | 0 |
| ACCOUNTS_PAYABLE_TITLES | 19 | **13** | 0 | **6** | 0 |

Pós-passagem 1:

- Notas no PG na janela: **14**
- Filial ≠ 2443: **0** (guard ativo)
- Duplicidade de nota: **0**
- Itens: **2** (iguais à origem — ver achado abaixo)
- Títulos: LINKED **15** · PENDING_INVOICE_LINK **4**

---

## 3. Achado crítico de origem (itens)

No XPERT, na mesma janela 03–09/07:

| Métrica | Valor |
|---------|-------|
| Notas | 14 |
| Notas **sem** linha em `ITENSMOVPRODUTOS` | **13** |
| Itens totais | **2** |
| Itens em LT | **0** |
| Itens em UN | **2** (1505/1506 Bardahl, nota 83471) |

O sync de itens está **fiel à origem**: não há combustível a granel em LT nesta janela no movimento de estoque ligado a essas notas. Os 20 movimentos LT observados em 30 dias estão **fora** de 03–09/07.

---

## 4. Tratamento cadastral

### 1505 / 1506 → IGNORED

| ERP | Descrição | Motivo |
|-----|-----------|--------|
| 1505 | ADITIVO FLEX 200ML BARDAHL | `NON_FUEL_MERCHANDISE` |
| 1506 | FLUIDO PARA RADIADOR ROSA 1L BARDAHL | `NON_FUEL_MERCHANDISE` |

Itens reconciliados: `metric_eligibility = EXCLUDED`, razões `IGNORED_PRODUCT` + `UNIT_CONVERSION_REQUIRED`, `volume_liters` nulo. **Sem** conversão UN→litros.

### Combustíveis 1, 2, 4, 1271, 1272 → MAPPED

Validação XPERT (filial 2443, unidade **LT**):

| ERP | Nome XPERT | Canônico |
|-----|------------|----------|
| 1 | ETANOL COMUM | `ETANOL_HIDRATADO` |
| 2 | GASOLINA COMUM | `GASOLINA_C_COMUM` |
| 4 | DIESEL S10 COMUM | `DIESEL_B_S10_COMUM` |
| 1271 | GASOLINA ADITIVADA | `GASOLINA_C_ADITIVADA` |
| 1272 | ETANOL ADITIVADO | `ETANOL_HIDRATADO` |

`erp_unit` no PG vinha `null` do sync PRODUCTS; unidade **LT** confirmada no XPERT antes do map. Artefato: `sprint-08-2-fuel-map-fix.json`.

Não há itens LT nesta janela para materializar `canonical_product_id` / `volume_liters` nos fatos — o mapeamento fica pronto para a próxima carga que trouxer esses produtos.

---

## 5. Passagem 2 (idempotente)

| Dataset | inserted | updated | unchanged | errors |
|---------|----------|---------|-----------|--------|
| INVOICES | 0 | 0 | **14** | 0 |
| ITEMS | 0 | 0 | **2** | 0 |
| TITLES | 0 | 0 | **19** | 0 |

Checkpoint permanece sem avanço.

---

## 6. Matriz XPERT × PG (após Etapa A)

| Métrica | XPERT | PG | Diferença |
|---------|-------|-----|-----------|
| Notas | 14 | 14 | 0 |
| Itens | 2 | 2 | 0 |
| Títulos | 19 | 19 (janela por `issue_date`) | 0* |
| Volume LT | 0 | 0 | 0 |
| Valor itens | 1016,48 | custo entregue 765,63** | — |
| PENDING_INVOICE_LINK | — | 4 | — |
| LINKED | — | 15 | — |

\* Contagem de títulos no PG filtrada por `issue_date` na janela.  
\*\* Custo comercial dos 2 itens UN (não combustível).

### Detalhes

| Check | Resultado |
|-------|-----------|
| Duplicidades | 0 |
| Vazamento de filial | 0 |
| Itens WAITING_FOR_INVOICE | 0 (nada pendente de cabeçalho) |
| Títulos PENDING | 4 (referência sem nota casável na base) |
| Produtos ignorados | 1505, 1506 |
| Produtos combustível mapeados | 1, 2, 4, 1271, 1272 |
| Canceladas / devoluções | 0 / 0 |
| 2ª execução | idempotente OK |

---

## 7. Rediscovery pós-sync

`REAL_COMPARABLE_PURCHASES = 0` (escopo: dados no PG)

Cobertura PG carregada: **03–09/07** (7 dias com notas).  
Grupos analisáveis: ainda só os 2 UN ignorados → não combustível / sem volume.

Gate compras para Etapa 3 **ainda não** satisfeito nesta janela (falta item LT com volume e custo).  
Gate cotações históricas para compras **passadas**: as 6 cotações novas **não** desbloqueiam T ≤ 09/07/2026 00:00 (ativadas depois).

---

## 8. Decisão

| Item | Status |
|------|--------|
| Sync manual 7d | **EXECUTADO** |
| Idempotência | **OK** |
| 1505/1506 | **IGNORED** |
| Combustíveis canônicos | **MAPPED** (prontos) |
| Itens combustível na janela | **Ausentes na origem XPERT** |
| Cotações de exemplo | **6 ativas** (operacionais) |
| Benchmark real | **BLOQUEADO** (sem compra LT + cotação histórica ≤ T) |
| Sprint 9 | **NÃO AUTORIZADA** |

### Próximo passo recomendado

Expandir sync manual para janela em que o XPERT tenha itens **LT** (ex.: trecho dos 30 dias com os 20 movimentos LT), reaplicar itens, confirmar `volume_liters = source_quantity`, e só então rediscovery. Alternativa operacional: aguardar próxima compra real **após** as cotações de exemplo já ativadas.
