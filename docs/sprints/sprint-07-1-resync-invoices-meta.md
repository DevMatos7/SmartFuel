# SPRINT 7.1 — RE-SYNC DE METADADOS NF-e

Data: 2026-07-09 · Filial ERP 2443 · Dataset `FUEL_PURCHASE_INVOICES` · Modo histórico/manual · Fonte UNSAFE

## Pré-carga

| Check | Resultado |
|-------|-----------|
| Contrato | **VALID** |
| `query_hash` (guard) | `996be7686714f9fbd9f31abb9bddae0ad3d0bf837d89544f39242e78efe5f032` |
| OUTER APPLY multiplica cabeçalhos | **Não** (0 multi-COMPENTRADAS; 1 linha / `source_invoice_id`) |
| Critério OUTER APPLY | `TOP 1 … ORDER BY ID_COMPENTRADAS DESC` |
| Chaves | 44 dígitos ou NULL |
| Filial ≠ 2443 | 0 |
| Duplicidade de chave na org | 0 |

### Perfil XPERT do dia (SAIDAS 1,9,21)

| Métrica | Valor |
|---------|-------|
| Notas no dia 09/07 | **3** (não 4) |
| Chaves preenchidas | **3** |
| Sem chave | **0** |
| `IMPORTOU_XML=1` | **2** |
| Frete / seguro / outras | **0** |

Nota: o perfil antigo “4 notas / 3 chaves / 1 sem chave” **não se reproduz** na fonte atual. No dia há exatamente 3 comprovantes de entrada.

`overlap_seconds=86400` faz a janela histórica puxar também **1 nota de 08/07** (`2042162`) → `rows_read=4` nas runs.

## Semântica XML

| Conceito | Campo | Significado |
|----------|-------|-------------|
| XML importado no ERP | `xml_imported_in_erp` ← `COMPENTRADAS.IMPORTOU_XML` | Flag do XPERT |
| Arquivo XML no sistema | `has_xml` / `has_xml_file` ← `nfe_xml_documents` + MinIO | Só com objeto armazenado |

`source_xml_available` foi renomeado na query para `source_xml_imported_in_erp` (migration `0017_xml_imported_erp`).

## Run 1

- ID: `f241953a-69b8-4818-80b7-21d4e581029d`
- Status: **COMPLETED**
- Lidos: **4** (3 do dia + 1 overlap 08/07)
- Inseridos: **0**
- Atualizados: **4**
- Inalterados: **0**
- Erros: **0**

### Metadados (dia 09/07)

- Notas com chave: **3**
- Notas sem chave: **0**
- Chaves inválidas: **0**
- Chaves duplicadas: **0**
- `IMPORTOU_XML=1`: **2**
- Frete total: **0**
- Seguro total: **0**
- Outras despesas: **0**

### Integridade

- Filial diferente: **0**
- Cabeçalhos duplicados: **0**
- Itens afetados: **0** (permanecem 2; frete zero → sem realocação)
- Títulos afetados: **0** (vínculo inalterado; 3 títulos do dia ainda sem NF por regra de link)
- Métricas reagregadas: **não** (custo entregue / frete diário inalterados em 0)

## Run 2

- ID: `df3223a0-cec4-4399-8666-c834a152fc38`
- Status: **COMPLETED**
- Lidos: **4**
- Inseridos: **0**
- Atualizados: **0**
- Inalterados: **4**
- Erros: **0**

Idempotência do enriquecimento via `COMPENTRADAS` **confirmada**.

## Checkpoint

- Antes: `watermark_value=null`, `source_upper_bound=null`
- Depois: inalterado
- Avançou: **não**

## Notas PG (09/07) após re-sync

| source_invoice_id | Doc | Série | access_key (44) | xml_imported_in_erp | Frete | Seguro | Outras | Total |
|-------------------|-----|-------|-----------------|---------------------|-------|--------|--------|-------|
| 2041821 | 83471 | 1 | 512607…464628 | false | 0 | 0 | 0 | 1016.48 |
| 2042163 | 179630 | 1 | 512607…424124 | true | 0 | 0 | 0 | 16.13 |
| 2042165 | 179721 | 1 | 512607…588727 | true | 0 | 0 | 0 | 21.98 |

Overlap enriquecido: `2042162` (entrada 08/07) também recebeu chave + flag.

## Decisão

Re-sync **autorizado e executado**. Cabeçalhos enriquecidos com chave e despesas (zeradas).

**Não homologa** reconciliação ERP × XML: arquivo continua dependendo de origem externa na Sprint 7.2.
