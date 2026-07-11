# SPRINT 6 — HOMOLOGAÇÃO REAL, ETAPA B — 7 DIAS

Gerado em: 2026-07-10 (UTC-4)

**Status geral:** **APROVADA ANALITICAMENTE** (2026-07-10). Separação CFOP × produto × unidade implementada. **Carga de 30 dias liberável após validação dos testes; incremental permanece bloqueado.**

---

## Decisão formal (2026-07-10)

| Item | Decisão |
|------|---------|
| Etapa A — dia único | **APROVADA** |
| Etapa B — 7 dias | **APROVADA ANALITICAMENTE** |
| Volume, receita, custo, margem, agregações (03/07–09/07) | **HOMOLOGADOS** |
| CFOP 5.667 | **INCLUDE_AS_SALE** / `FUEL_CANDIDATE` (DBA) |
| CFOP 5.102 | **INCLUDE_AS_SALE_GENERAL** / `NON_FUEL_BY_DEFAULT` (provisório fiscal) |
| CFOP 5.405 | **INCLUDE_AS_SALE_GENERAL_ST** / `NON_FUEL_BY_DEFAULT` (provisório fiscal) |
| Elegibilidade combustível | **CFOP venda + produto combustível + unidade válida** — não automática pelo CFOP |
| Produto 1507 (MAX DIESEL 200ML BARDAHL) | **Fora dos KPIs de combustível** até validar categoria/unidade |
| Preços por forma de pagamento | **PROVISÓRIOS** |
| Carga 30 dias | **LIBERÁVEL** após testes da separação CFOP × produto × unidade |
| Incremental | **BLOQUEADO** |
| Fonte | **UNSAFE** (`sa`) |
| Agenda automática | **BLOQUEADA** |
| Sprint 6 | **EM ANDAMENTO** |
| Sprint 7 | **NÃO AUTORIZADA** |

Versões de normalização documentadas nas runs `FUEL_SALES_ITEMS`:
- `normalization_version = FUEL_SALES_V2`
- `hash_schema_version = 2` (inclusão de `source_cfop` no hash)

---

## 1. Período e ambiente

| Item | Valor |
|------|-------|
| Período | `2026-07-03` a `2026-07-09` (inclusivo) |
| Posto | Matriz (`1edc5c8b-0ba1-405c-a000-03e61e31521e`) |
| erp_branch_id | `2443` |
| Hub SQL Server | `192.168.120.253` / `atxdados` |
| Fonte | **UNSAFE** (`sa`) |
| APP_ENV | `development` |
| Execução | Manual por ADMIN (`admin@test.com`) |
| Agenda automática | **Bloqueada** |
| Modo sync | `INCREMENTAL_TIMESTAMP` com janela histórica explícita |

---

## 2. Decisão do DBA sobre CFOP 5.667

| Item | Status |
|------|--------|
| Decisão fiscal/operacional | **Definida** — considerar como venda |
| Tratamento no código | `INCLUDE_AS_SALE` |
| Impacto nos 7 dias homologados | Nenhum — único registro estava cancelado |
| CFOPs desconhecidos (default) | `PENDING_REVIEW` → `PENDING_CFOP_CLASSIFICATION` |

---

## 3. Política final de classificação de CFOP

Política explícita em `backend/app/core/cfop_policy.py` — **natureza fiscal separada da elegibilidade de combustível**.

| CFOP | treatment | analytics_scope | review_status |
|------|-----------|-----------------|---------------|
| 5.656 / 5656 | `INCLUDE_AS_SALE` | `FUEL_CANDIDATE` | CONFIRMED |
| 5.667 / 5667 | `INCLUDE_AS_SALE` | `FUEL_CANDIDATE` | CONFIRMED |
| 5.102 / 5102 | `INCLUDE_AS_SALE_GENERAL` | `NON_FUEL_BY_DEFAULT` | PROVISIONAL_FISCAL_CONFIRMATION |
| 5.405 / 5405 | `INCLUDE_AS_SALE_GENERAL_ST` | `NON_FUEL_BY_DEFAULT` | PROVISIONAL_FISCAL_CONFIRMATION |
| Demais | `PENDING_REVIEW` | `PENDING` | PENDING_REVIEW |

KPI de combustível = venda CFOP candidata **e** produto canônico combustível **e** volume válido **e** não cancelado.

Documentação: `docs/integrations/xpert/cfop-policy.md`

---

## 4. Reconciliação do dia 09/07/2026

Artefato linha a linha: `docs/sprints/sprint-06-dia-reconciliacao-0907.json`

### Fórmula fechada

```
251 XPERT = 249 elegíveis + 1 cancelado + 1 não mapeado + 0 somente-XPERT + 0 somente-PG
```

| Métrica | XPERT (todos) | PG elegíveis | Δ | Explicação |
|---------|---------------|--------------|---|------------|
| Itens | 251 | 249 | **2** | 1 cancelado + 1 não mapeado |
| Volume (L) | 7.612,090 | 7.551,080 | **61,010** | 60,01 L cancelado + 1 L não mapeado |
| Receita líquida (R$) | 47.753,06 | 47.264,49 | **488,57** | R$ 435,67 cancelado + R$ 52,90 não mapeado |

### Por que “três ocorrências” mas Δ = 2?

| # | Ocorrência citada | Chave natural | Volume | Valor | Categoria reconciliação |
|---|-------------------|---------------|--------|-------|-------------------------|
| 1 | Cancelado | `1977692:2156497` | 60,01 L | R$ 435,67 | `CANCELLED` — motivo `CANCELLED_SALE` |
| 2 | Produto não mapeado | `1977639:2156441` | 1,00 L | R$ 52,90 | `UNMAPPED` — motivo `UNMAPPED_PRODUCT` |
| 3 | CFOP 5.667 | `1977692:2156497` | (mesmo item) | (mesmo item) | **Sobreposto ao cancelado** — CFOP visível no XPERT; no PG `source_cfop` ainda `null` (backfill pendente) |

**Conclusão do gate:** a divergência de contagem e de volume/receita do dia único está **integralmente explicada**. Não há itens somente no XPERT nem somente no PostgreSQL.

---

## 5. Linhas extraídas por dia

Comparação XPERT (todos os itens da filial) vs PostgreSQL (elegíveis):

| Dia | XPERT itens | PG elegíveis | Δ itens | XPERT volume (L) | PG volume (L) | Δ volume (L) | XPERT líquido (R$) | PG líquido (R$) | Δ líquido (R$) |
|-----|-------------|--------------|---------|------------------|---------------|--------------|--------------------|-----------------|----------------|
| 2026-07-03 | 332 | 327 | 5 | 7.199,719 | 7.025,797 | 173,922 | 43.046,33 | 41.716,29 | 1.330,04 |
| 2026-07-04 | 240 | 239 | 1 | 4.027,373 | 4.026,373 | 1,000 | 23.085,13 | 23.033,23 | 51,90 |
| 2026-07-05 | 162 | 160 | 2 | 2.678,178 | 2.650,338 | 27,840 | 16.166,39 | 15.931,63 | 234,76 |
| 2026-07-06 | 256 | 251 | 5 | 6.288,205 | 6.120,415 | 167,790 | 39.162,23 | 38.006,13 | 1.156,10 |
| 2026-07-07 | 252 | 248 | 4 | 6.103,274 | 6.099,274 | 4,000 | 37.644,01 | 37.484,41 | 159,60 |
| 2026-07-08 | 266 | 263 | 3 | 5.282,147 | 5.279,147 | 3,000 | 31.821,97 | 31.689,27 | 132,70 |
| 2026-07-09 | 251 | 249 | 2 | 7.612,090 | 7.551,080 | 61,010 | 47.753,06 | 47.264,49 | 488,57 |
| **Total** | **1.759** | **1.737** | **22** | **39.190,986** | **38.752,424** | **438,562** | **238.679,12** | **235.125,45** | **3.553,67** |

Artefato JSON: `docs/sprints/sprint-06-etapa-b-validate.json`

**Prova do total 7 dias:** Δ itens = 8 cancelados + 14 não mapeados = **22**. Δ volume = 424,562 L (cancelados) + 14,000 L (não mapeados) = **438,562 L**. Δ receita = R$ 2.931,07 + R$ 622,60 = **R$ 3.553,67**.

---

## 6. Itens aplicados e excluídos

### Sync Etapa B (run `a2d4e8ed-…`, 10/07/2026)

| Métrica | Valor |
|---------|-------|
| Status | `COMPLETED` |
| Lidos | 173 |
| Atualizados | 0 |
| Aplicados (novos) | 0 |
| Inalterados | 173 |
| Erros | 0 |

Os 1.759 fatos do período já existiam de cargas anteriores; o sync de 7 dias revalidou a janela sem alterações na origem.

### Exclusões no PostgreSQL (período completo)

| Motivo | Itens | Volume (L) | Receita líquida (R$) | Preservado no fato? |
|--------|-------|------------|----------------------|---------------------|
| `CANCELLED_SALE` | 8 | 424,562 | 2.931,07 | Sim (`is_cancelled=true`) |
| `UNMAPPED_PRODUCT` | 14 | 14,000 | 622,60 | Sim (visível na qualidade) |
| **Total excluídos** | **22** | **438,562** | **3.553,67** | — |

---

## 7. Volume XPERT versus PostgreSQL

| Escopo | Volume (L) |
|--------|------------|
| XPERT (todos os itens, filial 2443) | 39.190,986 |
| PostgreSQL elegíveis | 38.752,424 |
| PostgreSQL todos os fatos | 39.190,986 |
| Diferença XPERT − elegíveis | 438,562 — **100% explicada** por cancelados + não mapeados |

---

## 8. Receita XPERT versus PostgreSQL

| Escopo | Bruta (R$) | Desconto (R$) | Líquida (R$) | Custo (R$) |
|--------|------------|---------------|--------------|------------|
| PG elegíveis (7 dias) | 240.611,61 | 99,46 | 235.125,45 | 204.365,16 |
| PG excluídos | — | — | 3.553,67 | — |
| Margem bruta elegível | — | — | 30.760,29 (13,08%) | cobertura custo **100%** |

Diferença de receita líquida XPERT vs elegíveis: **R$ 3.553,67** — integralmente explicada.

---

## 9. Resultado por produto (elegíveis)

| Produto | Itens | Volume (L) | Receita líquida (R$) |
|---------|-------|------------|----------------------|
| DIESEL S10 COMUM | 179 | 13.721,544 | 95.635,26 |
| ETANOL COMUM | 487 | 10.722,458 | 47.719,60 |
| GASOLINA COMUM | 735 | 8.744,133 | 60.117,78 |
| ETANOL ADITIVADO | 147 | 3.200,460 | 14.828,70 |
| GASOLINA ADITIVADA | 189 | 2.363,829 | 16.824,11 |
| **Total** | **1.737** | **38.752,424** | **235.125,45** |

---

## 10. Resultado por CFOP

| CFOP | Classificação | Itens (todos) | Volume (L) | Líquido (R$) | Observação |
|------|---------------|---------------|------------|--------------|------------|
| 5.656 | `INCLUDE_AS_SALE` | 132 | 3.566,536 | 22.442,32 | Elegíveis |
| `null` | `null` | 1.627 | 35.624,450 | 216.236,80 | Maioria sem backfill de `source_cfop` em fatos anteriores à migration 0012 |

**Pendência:** backfill de `source_cfop` nos 1.627 fatos com CFOP `null` (inclui o cancelado `1977692:2156497`, que no XPERT é `5.667`). A classificação por CFOP nos indicadores depende desse backfill + decisão sobre `5.667`.

---

## 11. Cancelamentos e devoluções

| Tipo | Qtd | Volume (L) | Valor (R$) | Tratamento |
|------|-----|------------|------------|------------|
| Cancelamentos | 8 | 424,562 | 2.931,07 | Excluídos dos KPIs; fato preservado com `CANCELLED_SALE` |
| Devoluções (`INCLUDE_AS_RETURN`) | 0 | — | — | Nenhum CFOP classificado como devolução no período |

Distribuição dos cancelamentos por dia (inferida do Δ de itens): 03/07 (≈3), 04/07 (0), 05/07 (≈1), 06/07 (≈3), 07/07 (≈1), 08/07 (0), 09/07 (1 confirmado: `1977692:2156497`).

---

## 12. Produtos sem mapeamento

14 itens, 14 L, R$ 622,60 — **1 por dia** em média, todos com volume de 1 L:

| Dia | Venda | Item | Volume | Líquido |
|-----|-------|------|--------|---------|
| 2026-07-03 | 1976143 | 2154896 | 1 L | R$ 49,90 |
| 2026-07-03 | 1976162 | 2154916 | 1 L | R$ 42,90 |
| 2026-07-04 | 1976661 | 2155430 | 1 L | R$ 51,90 |
| 2026-07-05 | 1976730 | 2155500 | 1 L | R$ 39,90 |
| 2026-07-06 | 1976899 | 2155675 | 1 L | R$ 49,90 |
| 2026-07-06 | 1977079 | 2155860 | 1 L | R$ 42,90 |
| 2026-07-07 | 1977137 | 2155920 | 1 L | R$ 42,90 |
| 2026-07-07 | 1977202 | 2155988 | 1 L | R$ 49,90 |
| 2026-07-07 | 1977208 | 2155994 | 1 L | R$ 16,90 |
| 2026-07-07 | 1977309 | 2156099 | 1 L | R$ 49,90 |
| 2026-07-08 | 1977410 | 2156203 | 1 L | R$ 39,90 |
| 2026-07-08 | 1977428 | 2156222 | 1 L | R$ 49,90 |
| 2026-07-08 | 1977458 | 2156255 | 1 L | R$ 42,90 |
| 2026-07-09 | 1977639 | 2156441 | 1 L | R$ 52,90 |

Todos em quarentena analítica (`quarantined_item_count = 14`). Volume sem mapeamento preservado e visível.

---

## 13. Vendas sem custo

| Métrica | Valor |
|---------|-------|
| Itens elegíveis sem custo | **0** |
| Volume sem custo | 0 L |
| Custo convertido em zero | **Não** — `total_cost_amount` permanece `null` quando ausente |

---

## 14. Margens negativas

| Métrica | Valor |
|---------|-------|
| Itens com `margin_status=NEGATIVE` | **0** no período |
| Margens negativas preservadas | Mecanismo ativo; nenhuma ocorrência nos 7 dias |

---

## 15. Formas de pagamento provisórias

| Item | Valor |
|------|-------|
| Mapeamento VALOR1–4 → FORMAPGTO | **Provisório** (`mapping_status=PROVISIONAL`) |
| Formas de pagamento pendentes | **11** |
| Indicadores por forma de pagamento | **Não homologados** |
| Aviso na UI de preços | Ativo (`FuelPricesPage`) |
| Conclusões sobre dinheiro/débito/prazo/convênio | **Não publicar como definitivas** |

Volume, receita e margem geral dos 7 dias **podem** ser analisados; breakdown por forma de pagamento permanece provisório.

---

## 16. Duplicidades

| Verificação | Resultado |
|-------------|-----------|
| Chave natural `(org, station, source_sale_id, source_sale_item_id)` | **0 duplicatas** no período |
| Filiais diferentes de 2443 nos fatos | **0** (isolamento validado no contrato) |
| Validação de contrato `distinct_branch_ids` | `['2443']` apenas |

---

## 17. Correção retroativa testada

### Caso A — Inclusão do campo `source_cfop` (alteração de contrato)

| Etapa | Evidência |
|-------|-----------|
| Query hash alterado | Revalidação obrigatória antes do sync |
| Run `6a1cbf3d-…` (10/07/2026) | 186 lidos, **167 atualizados**, 186 aplicados, 0 inalterados |
| Hash diferente | `source_record_hash` recalculado com novo campo |
| Fato atualizado | 167 registros do dia 09/07 receberam `source_cfop` / `cfop_classification` |
| Agregado reconstruído | `fuel_sales_daily_metrics` reagregado na aplicação |
| Duplicidade | **0** |

### Caso B — Re-sync idempotente (sem mudança na origem)

| Etapa | Evidência |
|-------|-----------|
| Run `446bd208-…` (re-sync 09/07, 10/07/2026) | 173 lidos, **0 atualizados**, 173 inalterados |
| Comportamento | Pipeline detecta hash igual → não duplica nem regrava |

**Conclusão:** o pipeline trata correções retroativas do XPERT (hash muda → fato atualiza → agregado reconstrói) e permanece idempotente quando a origem não muda.

---

## 18. Agregações diárias

Comparação `fuel_sales_facts` (elegíveis) vs soma de `fuel_sales_daily_metrics` por dia:

| Dia | Itens fatos | Itens agregado | Volume fatos | Volume agregado | Líquido fatos | Líquido agregado | Match |
|-----|-------------|----------------|--------------|-----------------|---------------|------------------|-------|
| 2026-07-03 | 327 | 327 | 7.025,797 | 7.025,797 | 41.716,29 | 41.716,29 | ✓ |
| 2026-07-04 | 239 | 239 | 4.026,373 | 4.026,373 | 23.033,23 | 23.033,23 | ✓ |
| 2026-07-05 | 160 | 160 | 2.650,338 | 2.650,338 | 15.931,63 | 15.931,63 | ✓ |
| 2026-07-06 | 251 | 251 | 6.120,415 | 6.120,415 | 38.006,13 | 38.006,13 | ✓ |
| 2026-07-07 | 248 | 248 | 6.099,274 | 6.099,274 | 37.484,41 | 37.484,41 | ✓ |
| 2026-07-08 | 263 | 263 | 5.279,147 | 5.279,147 | 31.689,27 | 31.689,27 | ✓ |
| 2026-07-09 | 249 | 249 | 7.551,080 | 7.551,080 | 47.264,49 | 47.264,49 | ✓ |

API `trend` confere com agregações diárias.

---

## 19. Performance

| Operação | Duração / observação |
|----------|----------------------|
| Validação contrato FUEL_SALES_ITEMS | ~39 ms (amostra 5 linhas) |
| Extração XPERT 7 dias (script validate) | ~3–4 s |
| Sync API 7 dias (sem alterações) | ~2 s (173 inalterados) |
| Sync com 167 updates (backfill CFOP) | ~1 min |
| Consulta analytics summary 7 dias | < 1 s |

Tempos registrados em ambiente Docker local contra hub `192.168.120.253`.

---

## 20. Pendências

| # | Pendência | Bloqueia 30 dias? |
|---|-----------|-------------------|
| 1 | ~~Decisão DBA/fiscal sobre CFOP 5.667~~ | **Resolvido** — INCLUDE_AS_SALE / FUEL_CANDIDATE |
| 2 | ~~Separação CFOP × produto × unidade~~ | **Implementado** — testes 18 passed |
| 3 | Confirmação fiscal definitiva 5.102 / 5.405 | Não (provisório aceito para avançar) |
| 4 | Backfill `source_cfop` nos fatos com CFOP `null` | Parcial (relatórios por CFOP) |
| 5 | Confirmação definitiva mapeamento VALOR1–4 | Não (volume/receita/margem geral OK) |
| 6 | Homologação incremental (`source_updated_at`) | Sim para incremental |
| 7 | Homologação indicadores por forma de pagamento | Não para Etapa B geral |
| 8 | Carga de **30 dias** | **Liberável** — executar com política atual |
| 9 | Agenda automática em fonte UNSAFE | Permanece bloqueada |

---

## Critérios de aprovação — checklist

| Critério | Resultado |
|----------|-----------|
| Filiais diferentes de 2443 | **0** ✓ |
| Duplicidade chave natural | **0** ✓ |
| Diferença de volume | **Integralmente explicada** (438,562 L = cancelados + não mapeados) ✓ |
| Diferença de receita | **Integralmente explicada** (R$ 3.553,67) ✓ |
| Cancelamentos | Excluídos sem apagar o fato ✓ |
| Devoluções | Nenhuma; política pronta ✓ |
| CFOPs | 5.656 e 5.667 classificados; desconhecidos sinalizados via default ✓ |
| Produto não mapeado | Preservado e visível (14 itens) ✓ |
| Custo ausente | Não convertido em zero ✓ |
| Margem negativa | Preservada (0 ocorrências) ✓ |
| Agregação diária | Igual à soma dos fatos elegíveis ✓ |
| Mapeamento VALOR1–4 | Provisório ✓ |
| Fonte `sa` | UNSAFE ✓ |
| Agenda automática | Bloqueada ✓ |
| Correção retroativa | Comprovada (167 updates + re-sync idempotente) ✓ |

---

## Decisão

| Etapa | Status |
|-------|--------|
| Gate dia único — reconciliação 09/07 | **Fechado** |
| Gate dia único — CFOP 5.667 | **Fechado** (INCLUDE_AS_SALE) |
| Etapa B — 7 dias | **Executada** com divergências explicadas |
| Etapa C — 30 dias | **Liberável** (política CFOP × produto × unidade + testes OK) |
| Incremental contínuo | **Bloqueado** |

**Recomendação:** executar a carga de 30 dias com a política atual (5.102/5.405 fora dos KPIs de combustível). Manter bloqueio do incremental até confirmação de `source_updated_at`.

### Artefatos

- `docs/sprints/sprint-06-dia-reconciliacao-0907.json` — reconciliação linha a linha 09/07
- `docs/sprints/sprint-06-etapa-b-validate.json` — comparação diária XPERT vs PG
- `docs/sprints/sprint-06-etapa-b-data.json` — breakdown PostgreSQL 7 dias
- `backend/scripts/homolog_sprint6_line_reconcile.py` — reconciliação dia único
- `backend/scripts/homolog_cfop_profile_30d.py` — perfil read-only CFOPs
- `docs/sprints/sprint-06-cfop-profile-30d.json` — levantamento 30 dias (read-only)
