# Sprint 8.3 — Origem canônica dos itens de compra e homologação em litros

> Liberada após aprovação da Sprint 8.2 — Etapa A.  
> **Não** é Sprint 9. Benchmark real permanece bloqueado até compra posterior a cotação operacional válida.

---

## Decisão formal (entrada)

| Gate | Situação |
|------|----------|
| Sprint 8.2 Etapa A | **APROVADA** |
| Carga 7d (cabeçalhos/títulos) | **HOMOLOGADA** |
| Combustível em litros | **AINDA NÃO HOMOLOGADO** |
| Sprint 8.3 | **LIBERADA** |
| Benchmark sintético | **APROVADO** |
| Benchmark real | **BLOQUEADO** |
| Cotações de exemplo | `SYNTHETIC_TEST` / `analytics_eligible=false` |
| Sprint 9 | **NÃO AUTORIZADA** |
| Sprint 7.2 XML | **ADIADA** |
| Fonte XPERT | UNSAFE — `sa`; agenda e produção bloqueadas |

---

## Problema

O pipeline usa `ITENSMOVPRODUTOS`. Na janela 03–09/07/2026:

| Fonte | Resultado |
|-------|-----------|
| Cabeçalhos | 14 |
| Itens em `ITENSMOVPRODUTOS` | 2 (Bardahl UN 1505/1506) |
| Notas sem itens nessa origem | 13 |
| Litros de combustível | 0 |

`ITENSCOMPROVANTE` é a camada fiscal/documental. Em 30 dias há combustível LT nos produtos 1/2/4/1271/1272 no XPERT.

**Proibido:** `UNION ALL` cego das duas fontes sem matching de identidade.

---

## Etapa A — perfil read-only (concluída)

Script: `backend/scripts/homolog_sprint83_source_profile.py`  
Filial: **2443** · Sem apply no domínio.

### Resumo 7 / 30 / 90 dias

| Janela | Notas | Com MOV | Com FISCAL | Só fiscal | Ambas | Itens MOV | Itens FISCAL | Vol. LT combustível (ambas) |
|--------|-------|---------|------------|-----------|-------|-----------|--------------|------------------------------|
| 7d | 11 | 1 | 11 | 10 | 1 | 2 | 25 | **0** |
| 30d | 93 | 25 | 93 | 68 | 25 | 28 | 168 | **115 000** |
| 90d | 274 | 86 | 274 | 188 | 86 | 92 | 505 | **470 000** |

Artefatos:

- `docs/sprints/sprint-08-3-source-profile-7d.{md,json,csv}`
- `docs/sprints/sprint-08-3-source-profile-30d.{md,json,csv}`
- `docs/sprints/sprint-08-3-source-profile-90d.{md,json,csv}`

### Achados-chave

1. **Cobertura fiscal é universal nas notas de entrada** da janela (100% das notas com ≥1 linha em `ITENSCOMPROVANTE`).
2. **Movimento físico é parcial** (~27% das notas em 30d; ~31% em 90d).
3. **Volume LT de combustível fecha entre as duas fontes** no agregado (30d e 90d: MOV = FISCAL). Isso sugere que, para combustível granel, as quantidades batem quando ambas existem — mas há **muito mais linhas fiscais** (tributação / outros produtos / granularidade).
4. **Valores fiscais** usam `VLRTOTALITEM` (não `TOTAL`). Em 30d: MOV ≈ 619 550 · FISCAL ≈ 623 521 (diferença a explicar no matching, não a esconder).
5. Coluna de sequência fiscal candidata: **`DFE_NITEM`** — ainda **não comprovada** como equivalente à sequência de `ITENSMOVPRODUTOS`. Matching por sequência fica **bloqueado** até prova.
6. Campos fiscais confirmados: `CFOP`, `VLRDESCONTO`, `VLRFRETE`, `VLRSEGURO`, `VLROUTROS`, `VLRICMSITEM`, `VLRSUBSTITEM`, `VALOR_FECOP`, `VLRCUSTO`, `VLRUNITARIO`, `QTDE`.

### Chaves identificadas

| Entidade | Chave |
|----------|--------|
| Nota | `ID_COMPROVANTE` (+ `ID_FILIAL` / `ID_DB`) |
| Item fiscal | `ID_ITENSCOMPROVANTE` |
| Item movimento | via `MOVPRODUTOS` → `ITENSMOVPRODUTOS.ID_ITENSMOVPRODUTOS` (contrato atual) |
| Ligação nota↔fiscal | `ITENSCOMPROVANTE.ID_COMPROVANTE` |
| Ligação nota↔movimento | `MOVPRODUTOS.ID_COMPROVANTE` |

### Interpretação (não é erro automático)

13/14 notas sem itens em MOV na janela 8.2 Etapa A é **cobertura de fonte**, não falha de sync. Possíveis causas:

- nota sem movimento de estoque relevante;
- chave COMPROVANTES↔MOV incompleta;
- itens só na camada fiscal.

### Dia recomendado para Etapa B

| Critério | Valor |
|----------|--------|
| **Dia** | **2026-06-20** |
| Notas com combustível LT | 2 |
| Linhas | 2 |
| Volume LT | 10 000 |
| Custo ~ | 32 579 |

(Menor número de notas com produto ∈ {1,2,4,1271,1272}, unidade LT, qtde > 0, no perfil 30d.)

Alternativas com 2 notas: `2026-06-24`, `2026-06-26`. Em 90d o menor observado foi `2026-05-21`.

---

## Cotações de exemplo

Migration: `0019_sprint83_quote_origin`

| Campo | Valor nas 6 cotações de exemplo |
|-------|----------------------------------|
| `origin` | `SYNTHETIC_TEST` |
| `analytics_eligible` | `false` |

Artefato: `docs/sprints/sprint-08-3-synthetic-quotes.json`

Efeitos:

- excluídas de `QuoteCandidateService` (benchmark / comparação);
- **não** usam em indicadores operacionais nem homologação com compra real;
- no-hindsight continua: `activated_at` atual nunca compara com compra histórica de julho.

Cotações reais futuras devem usar `origin=MANUAL_OPERATIONAL`, evidência, `quoted_at` / `available_at` e só comparar compras com `reference_datetime >= activated_at`.

---

## Precedência provisória (após perfil; a formalizar na Etapa B+)

| Dimensão | Precedência |
|----------|-------------|
| Quantidade / volume | 1) MOV válido → 2) fiscal fallback só se regras explícitas → 3) sem volume |
| CFOP / NCM / tributos / frete item | FISCAL |
| Custo entregue | metodologia Sprint 7 (`commercial_delivered_cost`); não substituir cegamente |
| Dupla contagem | **proibida** — matching antes de um único item de domínio |

Fallback fiscal (volume) exige: sem MOV correspondente, L/LT, qtde > 0, combustível mapeado, sem duplicidade, nota ativa, fechamento com cabeçalho.

---

## Etapas seguintes (ainda não executadas)

| Etapa | Conteúdo | Status |
|-------|----------|--------|
| **A** | Perfil 7/30/90d | **CONCLUÍDA** |
| **B** | Contratos MOV+FISCAL, matching, resolution, sync **1 dia** (`2026-06-20`) | **PENDENTE** |
| **C** | Sete dias | Após aprovação de B |
| **D** | Trinta dias | Após aprovação de C |

**Não** migrar o pipeline para `ITENSCOMPROVANTE` sem resolução canônica.  
**Não** executar 7d/30d completos antes do dia único.  
**Não** antecipar Sprint 9.

---

## Produtos

| ERP | Tratamento |
|-----|------------|
| 1505, 1506 | `IGNORED` / `NON_FUEL_MERCHANDISE` |
| 1, 2, 4, 1271, 1272 | Combustível mapeado (manter) |

---

## Fora de escopo

XML, Sefaz, escrita no XPERT, Brent/dólar, índices externos, benchmark com cotação posterior à compra, cotações históricas inventadas, Sprint 9.
