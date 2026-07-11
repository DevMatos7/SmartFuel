# SPRINT 6 — HOMOLOGAÇÃO REAL, ETAPA C — 30 DIAS

Gerado em: 2026-07-10 (UTC-4)

**Status:** **APROVADA OPERACIONALMENTE** (2026-07-10). Runs de fechamento **COMPLETED**, erros bloqueantes **0**, checkpoint de vendas **não avançado**. Ressalva analítica anterior (produto 1136) **resolvida**.

---

## Fechamento operacional (pós-ressalva)

### Diagnóstico produto 1136

| Verificação | Resultado |
|-------------|-----------|
| Existe na filial 2443? | **Sim** |
| Nome | ADITIVO BARDAHL FLEX - 24/200 ML |
| ATIVO | **false** (inativo) |
| Omitido por `PRODUCTS` (`ATIVO = 1`)? | **Sim** — cenário A |
| Item da venda | `1971639:2150248`, CFOP 5.102, R$ 49,90 |

### Correções aplicadas

1. Query `products.sql`: remove filtro `ATIVO = 1` (mantém `source_active`).
2. Sync PRODUCTS: **83** produtos inseridos (inclui 1136 como `PENDING`, `source_active=false`).
3. Defesa histórica: `erp_product_id` nullable + `source_product_id` + motivo `MISSING_ERP_PRODUCT_REFERENCE` (migration 0014).
4. Reexecução 30 dias → **COMPLETED**.

### Runs de fechamento

| Run | Status | Inseridos | Atualizados | Inalterados | Erros | Checkpoint |
|-----|--------|-----------|-------------|-------------|-------|------------|
| PRODUCTS `14b0ddc0-…` | COMPLETED | 83 | 0 | 1.250 | 0 | (dataset PRODUCTS) |
| Vendas pass1 `caca3e63-…` | **COMPLETED** | **1** | 0 | 7.710 | **0** | **não avançou** |
| Vendas pass2 `35cda7dd-…` | **COMPLETED** | 0 | 0 | **7.711** | **0** | **não avançou** |

### Fato 1136 após correção

| Campo | Valor |
|-------|-------|
| Persistido | Sim (`7456` fatos no período) |
| erp_product | PENDING / inativo na origem |
| Elegibilidade | `EXCLUDED` |
| Motivos | `UNMAPPED_PRODUCT` + `EXCLUDED_NON_FUEL_PRODUCT` |
| KPI combustível | **Não entra** |
| Agregações | **30/30** |
| Volume/receita elegíveis | **Inalterados** (160.739,87 L / R$ 976.244) |

---
## 1. Ambiente e período

| Item | Valor |
|------|-------|
| Período | `2026-06-10` a `2026-07-09` (inclusivo) |
| Posto | Matriz (`1edc5c8b-0ba1-405c-a000-03e61e31521e`) |
| erp_branch_id | `2443` |
| Dataset | `FUEL_SALES_ITEMS` |
| Acionamento | MANUAL / ADMIN (`admin@test.com`) |
| Fonte | **UNSAFE** (`sa`) |
| Agenda automática | **Bloqueada** |
| Modo | Carga histórica com intervalo explícito |
| Incremental contínuo | **Não utilizado** |
| Backup pré-carga | `docs/sprints/backup_pre_etapa_c_20260610_20260709.dump` |
| Baseline | `docs/sprints/sprint-06-etapa-c-baseline.json` |

### Baseline pré-carga

| Métrica | Valor |
|---------|-------|
| Fatos no período | 7.455 |
| Métricas diárias | 118 |
| Última run | `446bd208-…` COMPLETED |
| Query hash | `8961f530ad1da7dcdd63710893b06f3f4fc71ee8f8c9a8f944d08da051a66e9f` |
| normalization_version | `FUEL_SALES_V2` |
| hash_schema_version | `2` |
| cfop_policy_version | `CFOP_POLICY_V2_FISCAL_VS_FUEL_KPI` |
| Produtos ERP não mapeados | 1.244 |
| Checkpoint watermark (antes) | `2026-07-10T14:09:20.529565+00:00` |

### Bloqueios mantidos

- scheduler / agenda UNSAFE
- incremental contínuo
- breakdown definitivo por forma de pagamento
- produção com fonte UNSAFE

---

## 2. Query hash e versões de normalização

| Campo | Valor |
|-------|-------|
| query_hash | `8961f530ad1da7dcdd63710893b06f3f4fc71ee8f8c9a8f944d08da051a66e9f` |
| normalization_version | `FUEL_SALES_V2` |
| hash_schema_version | `2` |
| cfop_policy_version | `CFOP_POLICY_V2_FISCAL_VS_FUEL_KPI` |

Alteração de runtime aplicada nesta etapa: janela histórica explícita **ignora watermark** e **não avança checkpoint**.

---

## 3. Run ID e duração

### Passagem 1 (carga)

| Campo | Valor |
|-------|-------|
| Run ID | `de31376c-ab71-4087-805e-55c141003c2b` |
| Status | **PARTIAL** |
| Duração | ~68 s (wall) / ~54 s (started→finished) |
| window_start | `2026-06-09T00:00:00Z` (início − overlap do dataset) |
| window_end | `2026-07-10T00:00:00Z` (exclusivo) |

### Passagem 2 (idempotência)

| Campo | Valor |
|-------|-------|
| Run ID | `d942257b-a085-4619-8c75-df58a99966e3` |
| Status | **PARTIAL** (mesmo erro residual) |
| Duração | ~44 s |

---

## 4. Linhas extraídas, staged e aplicadas

| Métrica | Pass 1 | Pass 2 |
|---------|--------|--------|
| rows_read | 7.711 | 7.711 |
| rows_staged | 7.711 | 7.711 |
| rows_valid | 7.711 | 7.711 |
| rows_inserted | 0 | 0 |
| rows_updated | 7.578 | 0 |
| rows_unchanged | 132 | **7.710** |
| rows_applied | 7.578 | 0 |
| rows_error | **1** | **1** |
| rows_quarantined | 0 | 0 |

> 7.711 inclui overlap de ~1 dia antes de 10/06. No período estrito 10/06–09/07: XPERT **7.456** / PostgreSQL **7.455**.

### Erro único (PARTIAL explicado)

| Campo | Valor |
|-------|-------|
| source_key | `1971639:2150248` |
| source_product_id | `1136` |
| source_cfop | `5.102` |
| cancelled | false |
| Causa | Produto ERP `1136` **ausente** em `erp_products` → apply retorna `ERROR` |
| Impacto | 1 fato não persistido (venda geral 5.102) |
| Contaminação de KPI combustível | **Nenhuma** |

---

## 5. Isolamento da filial

| Verificação | Resultado |
|-------------|-----------|
| `source_branch_id ≠ 2443` | **0** |
| Filial distinta nos fatos | **0** |

---

## 6. Duplicidade da chave natural

| Verificação | Resultado |
|-------------|-----------|
| Duplicatas `(source_sale_id, source_sale_item_id)` no período | **0** |

---

## 7. Resultado por CFOP

### Perfil XPERT (read-only, período estrito)

| CFOP | Ativos | Cancelados | Política | Escopo |
|------|--------|------------|----------|--------|
| 5.656 | 7.343 | 67 | INCLUDE_AS_SALE | FUEL_CANDIDATE |
| 5.667 | 18 | 1 | INCLUDE_AS_SALE | FUEL_CANDIDATE |
| 5.102 | 25 | 1 | INCLUDE_AS_SALE_GENERAL | NON_FUEL_BY_DEFAULT |
| 5.405 | 1 | 0 | INCLUDE_AS_SALE_GENERAL_ST | NON_FUEL_BY_DEFAULT |

### PostgreSQL aplicado

| CFOP | Situação | Itens | Volume (L) | Líquido (R$) |
|------|----------|-------|------------|--------------|
| 5.656 | elegível (+warnings) | 7.296 | 160.117,11 | 972.073,85 |
| 5.667 | elegível (+warnings) | 18 | 622,76 | 4.170,15 |
| 5.656 | excluído (não cancelado) | 47 | 97,00 | 4.194,62 |
| 5.656 | cancelado | 67 | 3.646,63 | 24.372,71 |
| 5.667 | cancelado | 1 | 60,01 | 435,67 |
| 5.102 | excluído ativo | 24 | null* | 1.342,60 |
| 5.102 | cancelado | 1 | null* | 86,90 |
| 5.405 | excluído | 1 | null* | 12,90 |

\* Volume `null`: unidade nula + CFOP geral → sem conversão automática (`UNIT_CONVERSION_REQUIRED` / exclusão não combustível).

### Gate CFOP × KPI combustível

| Gate | Resultado |
|------|-----------|
| 5.102 em KPI combustível | **0** |
| 5.405 em KPI combustível | **0** |
| Δ 5.102 ativos XPERT 25 vs PG 24 | **1** = produto `1136` não cadastrado (erro da run) |

---

## 8. Resultado por produto (elegíveis)

| Produto canônico | Família | Itens | Volume (L) | Líquido (R$) |
|------------------|---------|-------|------------|--------------|
| Etanol hidratado | ETHANOL | 2.669 | 58.344,75 | 261.940,37 |
| Diesel B S10 comum | DIESEL_B_S10 | 802 | 56.478,93 | 396.101,66 |
| Gasolina C comum | GASOLINE_C | 3.101 | 36.743,34 | 252.873,38 |
| Gasolina C aditivada | GASOLINE_C | 742 | 9.172,86 | 65.328,59 |
| *(demais via ERP: etanol aditivado etc.)* | | | | |

Total elegível: **7.314** itens / **160.739,87 L** / **R$ 976.244,00**

---

## 9. Resultado por unidade

| source_unit | Itens | Observação |
|-------------|-------|------------|
| `null` | 7.455 | XPERT não envia unidade; CFOP bomba assume litros; CFOP geral não converte |

Nenhuma unidade UN/PC/CX observada na origem neste período.

---

## 10. Cancelamentos

| Motivo | Itens | Volume (L) | Líquido (R$) |
|--------|-------|------------|--------------|
| `CANCELLED_SALE` | 69 | 3.706,64 | 24.895,28 |

Fatos preservados; fora dos KPIs.

---

## 11. Produtos não mapeados

| Motivo | Itens | Volume (L) | Líquido (R$) |
|--------|-------|------------|--------------|
| `UNMAPPED_PRODUCT` | 59 | 49,00 | 2.937,70 |
| `UNMAPPED_PRODUCT` + `NEGATIVE_GROSS_MARGIN` | 2 | 48,00 | 2.063,52 |
| **Total não mapeados** | **61** | **97,00** | **5.001,22** |

Visíveis na qualidade (`unmapped_item_count=61`).

---

## 12. Produtos não combustíveis

| Motivo | Itens | Líquido (R$) |
|--------|-------|--------------|
| `EXCLUDED_NON_FUEL_PRODUCT` | 11 | 548,90 |

Inclui **MAX DIESEL 200ML BARDAHL (1507)**: 11 itens, volume null, **fora dos KPIs de combustível**.

---

## 13. Conversões de unidade pendentes

Não há itens com `UNIT_CONVERSION_REQUIRED` isolado no agrupamento final porque:

- CFOP bomba + unit null → litros
- CFOP geral (5.102/5.405) → exclusão `EXCLUDED_NON_FUEL_PRODUCT` (precedência sobre unidade)

Comportamento alinhado à política documentada.

---

## 14. Volume XPERT versus PostgreSQL

| Escopo | Volume (L) |
|--------|------------|
| XPERT total (todos CFOPs, período) | ~164.570,51 |
| PG elegível (KPI combustível) | **160.739,87** |
| PG cancelados | 3.706,64 |
| PG não mapeados | 97,00 |
| PG não combustível / unit null | volume não convertido (não entra no KPI) |

Diferença KPI vs XPERT bruto: **integralmente explicada** por cancelamentos + não mapeados + venda geral 5.102/5.405 + 1 item sem produto ERP.

---

## 15. Receita XPERT versus PostgreSQL

| Escopo | Líquido (R$) |
|--------|--------------|
| PG elegível | **976.244,00** |
| PG bruto elegível | 996.211,34 |
| Descontos elegíveis | 511,66 |
| Excluídos (cancelados + unmapped + non-fuel) | ~30.445 |

Diferenças **explicadas** pelas regras de elegibilidade.

---

## 16. Custo e cobertura

| Métrica | Valor |
|---------|-------|
| Custo total elegível | R$ 856.296,42 |
| Cobertura de custo | **100%** |
| Custo ausente convertido em zero | **0** |
| Itens elegíveis sem custo | **0** |

---

## 17. Margem e margens negativas

| Métrica | Valor |
|---------|-------|
| Margem bruta | R$ 119.947,58 |
| Margem / L | R$ 0,7462 |
| Margem % | **12,29%** |
| Itens `margin_status=NEGATIVE` elegíveis | **0** |
| Warnings `NEGATIVE_GROSS_MARGIN` (com unmapped) | 2 (excluídos) |
| Warnings `MIXED_OR_UNALLOCATED_PAYMENT` | 7.308 elegíveis com aviso (pagamento provisório) |

Formas de pagamento permanecem **provisórias** — não homologar breakdown.

---

## 18. Agregações dos 30 dias

| Verificação | Resultado |
|-------------|-----------|
| Dias com match fato ↔ agregado | **30 / 30** |
| Dias sem movimento no período | 0 (todos com movimento) |

Cada dia: `fuel_sales_daily_metrics` = soma dos fatos elegíveis.

---

## 19. Qualidade dos dados

| Indicador | Valor |
|-----------|-------|
| Não mapeados | 61 itens / 97 L |
| Sem custo | 0 |
| Quarentena analítica | 72 |
| Formas pagamento pendentes | 11 |
| Produto ERP ausente (apply error) | 1 (`1136`) |

### Exclusões por motivo (sem “outros”)

| Motivo | Itens |
|--------|-------|
| CANCELLED_SALE | 69 |
| UNMAPPED_PRODUCT | 59 |
| UNMAPPED_PRODUCT + NEGATIVE_GROSS_MARGIN | 2 |
| EXCLUDED_NON_FUEL_PRODUCT | 11 |
| PENDING_CFOP_CLASSIFICATION | 0 |
| UNIT_CONVERSION_REQUIRED (isolado) | 0 |
| INVALID_VOLUME | 0 |
| MISSING_COST | 0 |

---

## 20. Performance

| Operação | Tempo |
|----------|-------|
| Pass 1 (7.711 linhas, 7.578 updates) | ~54–68 s |
| Pass 2 (7.710 unchanged) | ~28–44 s |
| Validação XPERT+PG | ~5 s |

---

## 21. Segunda execução idempotente

| Critério | Pass 2 |
|----------|--------|
| Novos fatos | **0** |
| Atualizados | **0** |
| Inalterados | **7.710** |
| Duplicidades | **0** |
| Summary volume/receita/margem | **Idêntico** ao pass 1 |
| Mesmo erro residual | 1 (`1136`) |

**Idempotência comprovada.**

---

## 22. Checkpoint

| Campo | Antes | Depois (pass 1 e 2) |
|-------|-------|---------------------|
| watermark_value | `2026-07-10T14:09:20.529565+00:00` | **igual** |
| checkpoint_before / after na run | mesmo valor | **não avançou** |

Carga histórica com janela explícita **não cria avanço incremental**, conforme exigido enquanto `source_updated_at` não está confirmado.

---

## 23. Pendências

| # | Item | Bloqueia? |
|---|------|-----------|
| 1 | Produto ERP `1136` ausente (1 venda 5.102) | Não para KPI combustível; sim para COMPLETED 100% |
| 2 | Confirmação fiscal definitiva 5.102 / 5.405 | Não (provisório aceito) |
| 3 | Mapeamento VALOR1–4 / formas de pagamento | Não para volume/margem geral |
| 4 | Homologação `source_updated_at` / incremental | **Sim para incremental** |
| 5 | Backfill `source_cfop` legado (se restar null fora desta janela) | Relatórios |
| 6 | Agenda UNSAFE | Permanece bloqueada |

---

## 24. Decisão de aprovação

| Gate | Exigência | Resultado |
|------|-----------|-----------|
| Run principal | COMPLETED ou PARTIAL explicado | **PARTIAL explicado** (produto 1136) ✓ |
| Vazamento entre filiais | Zero | **0** ✓ |
| Duplicidade de fatos | Zero | **0** ✓ |
| Diferença de itens | Explicada | ✓ (1 sem ERP product + exclusões) |
| Diferença de volume | Explicada | ✓ |
| Diferença de receita | Explicada | ✓ |
| CFOP 5.102/5.405 em KPIs combustível | Zero | **0** ✓ |
| Produto 1507 em volume combustível | Zero | **0** ✓ |
| Custo ausente → zero | Zero | **0** ✓ |
| Agregações diárias | 30/30 | **30/30** ✓ |
| Segunda execução | Idempotente | ✓ |
| Agenda UNSAFE | Bloqueada | ✓ |
| Checkpoint incremental | Não avançado | ✓ |
| Formas de pagamento | Provisórias | ✓ |

### Decisão formal

| Item | Status |
|------|--------|
| Etapa C — 30 dias (analítica) | **APROVADA** |
| Etapa C — 30 dias (operacional) | **CONCLUÍDA** — runs COMPLETED |
| Volume, receita, custo e margem | **HOMOLOGADOS** |
| Agregações | **HOMOLOGADAS — 30/30** |
| Idempotência | **HOMOLOGADA** |
| Isolamento multi-filial | **HOMOLOGADO** |
| Produto 1136 | **Resolvido** (sync inativos + fato preservado fora dos KPIs) |
| Incremental | **BLOQUEADO** (aguarda `source_updated_at`) |
| Agenda UNSAFE | **BLOQUEADA** |
| Sprint 6 | **EM ANDAMENTO** — próximo gate: incremental |
| Sprint 7 | **NÃO AUTORIZADA** |

### Artefatos

- `docs/sprints/sprint-06-etapa-c-baseline.json`
- `docs/sprints/backup_pre_etapa_c_20260610_20260709.dump`
- `docs/sprints/sprint-06-etapa-c-run-pass1.json`
- `docs/sprints/sprint-06-etapa-c-run-pass2.json`
- `docs/sprints/sprint-06-etapa-c-validate.json`
- `docs/sprints/sprint-06-cfop-profile-30d.json`
