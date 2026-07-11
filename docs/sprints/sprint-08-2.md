# Sprint 8.2 — Prontidão de dados para benchmark real

> Autorizada após aprovação formal da Sprint 8.1.  
> **Não** é Sprint 9. Benchmark em lote 7/30 dias permanece bloqueado.

---

## Decisão registrada (entrada)

| Gate | Situação |
|------|----------|
| Sprint 8.1 | **APROVADA** |
| Homologação sintética E2E | **APROVADA** |
| Proteção contra hindsight | **APROVADA** |
| Homologação real | **BLOQUEADA** por disponibilidade/qualidade de dados |
| Próxima fase | **Sprint 8.2 — prontidão de dados reais** |
| Carga benchmark 7d / 30d | **BLOQUEADA** |
| Sprint 7.2 XML | **ADIADA** |
| Sprint 9 | **NÃO AUTORIZADA** |

---

## Correção semântica da descoberta 8.1

A janela de 90 dias **pesquisada** no PG não implica 90 dias **carregados**.

| Métrica | Valor atual (Matriz / filial 2443) |
|---------|-------------------------------------|
| Período pesquisado (ex.: 90d) | ~2026-04-12 → 2026-07-11 |
| Primeiro dia de compra no PG | **2026-07-08** |
| Último dia de compra no PG | **2026-07-09** |
| Dias com compras no PG | **2** |
| Notas no PG | **4** |
| Itens no PG | **2** |

Interpretação correta:

- `compras comparáveis nos dados disponíveis no PG = 0`
- **não** afirmar: `compras comparáveis no XPERT em 90 dias = 0`

Scripts atualizados:

- `homolog_sprint81_discovery.py` — passa a emitir `pg_loaded_coverage` e escopo `available_postgres_data_only`
- `homolog_sprint82_coverage.py` — compara XPERT × PG em 1 / 7 / 30 dias + diagnóstico 1505/1506

Artefatos: `docs/sprints/sprint-08-2-coverage.*`, `sprint-08-2-product-diag.json`.

---

## Etapa A — cobertura real (executada em modo leitura)

| Janela | Notas XPERT | Notas PG | Gap notas | Itens XPERT | Itens PG | Gap itens |
|--------|-------------|----------|-----------|-------------|----------|-----------|
| 1 dia (hoje) | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 dias | 11 | 4 | **7** | 2 | 2 | 0 |
| 30 dias | **93** | 4 | **89** | **28** | 2 | **26** |

Unidades no XPERT (30d): `LT=20`, `UN=7`, `KG=1`.  
Unidades no PG: apenas `UN=2` (os dois itens sincronizados).

Conclusão da Etapa A: o pipeline de compras **não** está homologado além do recorte mínimo da Sprint 7.1. Há movimento real de combustível em litros no XPERT que **ainda não está no PostgreSQL**.

Agenda XPERT permanece bloqueada; expansões continuam **manuais**.

---

## Três bloqueios independentes — diagnóstico

### 1. Produtos 1505 / 1506 — **não mapear como combustível**

Consulta XPERT (filial 2443):

| ERP ID | Nome | Unidade | NCM |
|--------|------|---------|-----|
| 1505 | **ADITIVO FLEX 200ML BARDAHL** | UN | 38119090 |
| 1506 | **FLUIDO PARA RADIADOR ROSA 1L BARDAHL** | UN | 38249941 |

São mercadoria de loja (aditivo / fluido), **não** combustível a granel.

Ação cadastral correta:

- **Não** vincular a `ETHANOL` / `GASOLINE_C` / `DIESEL_*`
- Preferir `mapping_status = IGNORED` (motivo: não combustível / fora do escopo de benchmark de compra a granel)
- Volume `UN` sem fator → `UNIT_CONVERSION_REQUIRED` é comportamento esperado

### 2. Volume = 0 — esperado para 1505/1506

Regra do apply (`FuelPurchasesApplyService`):

- `volume_liters` só é preenchido se `source_unit ∈ {L, LT, LITRO, LITROS, LITER, LITERS}`
- Unidade `UN` → exclusão `UNIT_CONVERSION_REQUIRED`, sem estimar litros pelo valor

Para combustível real no XPERT (abaixo), a unidade já é **`LT`** → após sync, `volume_liters` deve espelhar `source_quantity` sem conversão inventada.

### 3. Nenhuma cotação histórica ativada

| Métrica | Valor |
|---------|-------|
| Cotações com `activated_at` no posto | **0** |

Caminhos válidos (inalterados):

1. Operação futura — ativar cotações **antes** da compra  
2. Import legado **somente** com evidência verificável (`origin = LEGACY_DOCUMENTED_IMPORT` — ainda a modelar; **não** existe no código hoje)

**Proibido:** retroagir `activated_at` só para gerar benchmark.

---

## Combustível real no XPERT (30 dias) — universo potencial

Candidatos a granel (unidade `LT`) na filial 2443:

| ERP ID | Nome | Unidade | Movimentos | Qtde total (LT) |
|--------|------|---------|------------|-----------------|
| 4 | DIESEL S10 COMUM | LT | 6 | 40 000 |
| 1 | ETANOL COMUM | LT | 6 | 35 000 |
| 2 | GASOLINA COMUM | LT | 6 | 30 000 |
| 1272 | ETANOL ADITIVADO | LT | 1 | 5 000 |
| 1271 | GASOLINA ADITIVADA | LT | 1 | 5 000 |

Esses produtos **não** estão nos 2 itens do PG. São o alvo da Etapa A (sync 7→30d) + Etapa B (mapeamento canônico).

---

## Plano da Sprint 8.2 (próximas execuções)

### Etapa A — expandir carga manual

1. Sync manual Matriz: janela **7 dias** (INVOICES → ITEMS → AP), com `unsafe_homologation_acknowledged`
2. Reconciliar contagens XPERT × PG (script `homolog_sprint82_coverage.py`)
3. Se gap aceitável, expandir para **30 dias**
4. Não habilitar agenda

### Etapa B — saneamento cadastral

1. Ignorar 1505/1506 (não combustível)
2. Mapear 1, 2, 4, 1271, 1272 → canônicos corretos (família + variante)
3. Mapear fornecedores ERP → distribuidoras quando houver evidência
4. Reaplicar / re-sync itens após mapeamento (compras não têm reconcile automático como vendas)

### Etapa C — volume

Para cada item combustível pós-sync:

| Campo | Esperado |
|-------|----------|
| `source_quantity` | > 0 |
| `source_unit` | LT (ou L) |
| `volume_liters` | = quantity |
| exclusão de conversão | ausente |

### Etapa D — cotações

Cobertura por posto/produto; ativar cotações operacionais futuras **antes** das compras. Import legado só com evidência.

### Etapa E — nova descoberta

Reexecutar matriz só com: produto mapeado + volume válido + custo + cotação `activated_at <= T`.

---

## Critério para desbloquear Etapa 3 (compra real)

Pelo menos um grupo com:

- nota não cancelada  
- `canonical_product_id` de combustível  
- `volume_liters > 0`  
- `commercial_delivered_cost > 0`  
- `reference_datetime`  
- ≥1 cotação com `activated_at <= T` elegível ao volume  

Preferencialmente: fornecedor → distribuidora mapeada.

---

## Paralelo (fechamento Sprint 8 — código)

Pode avançar **sem** desbloquear 7d/30d de benchmark:

- pytest completo / Vitest / build Vite  
- APIs `trend` e `by-*`  
- UI de parâmetros  
- exportações só de snapshots  
- migração em banco vazio/teste  

---

## Status ao fim deste relatório

| Item | Status |
|------|--------|
| Distinção período pesquisado × PG carregado | **Feito** |
| Cobertura XPERT×PG 1/7/30d | **Feito (leitura)** |
| Diagnóstico 1505/1506 | **Feito — não são combustível** |
| Universo combustível XPERT 30d | **Identificado (IDs 1,2,4,1271,1272)** |
| Sync 7d (Etapa A homologação) | **Feito — aprovado** (ver `sprint-08-2-etapa-a.md`) |
| Mapeamento combustível 1/2/4/1271/1272 | **Feito** |
| Cotações de exemplo | Criadas; na 8.3 marcadas `SYNTHETIC_TEST` |
| Combustível LT no PG | **Pendente** → Sprint 8.3 Etapa B (`2026-06-20`) |
| Etapa 3 compra real / benchmark | **Ainda bloqueada** |
