# Sprint 7.1 — Contratos reais, apply e homologação de 1 dia

## Status

| Item | Estado |
|------|--------|
| Queries reais | IMPLEMENTADAS (DTACONTA) |
| Contratos | VALID (filial 2443) |
| FuelPurchasesApplyService | IMPLEMENTADO |
| Agregação | IMPLEMENTADA |
| Homologação 1 dia (2026-07-09) | EXECUTADA |
| XML | ADIADO (7.2) |
| Incremental watermark | NÃO VALIDADO |
| Sprint 8 | NÃO AUTORIZADA |

## Objetos XPERT

| Dataset | Tabelas | Chave |
|---------|---------|-------|
| FUEL_PURCHASE_INVOICES | COMPROVANTES | ID_COMPROVANTE |
| FUEL_PURCHASE_ITEMS | ITENSMOVPRODUTOS + MOVPRODUTOS + COMPROVANTES + PRODUTOS | ID_ITENSMOVPRODUTOS |
| ACCOUNTS_PAYABLE_TITLES | CONTASPAGAR (+ CONTASPAGARBAIXA) | ID_CONTASPAGAR |

Filtro de entradas: `SAIDAS_ENTRADAS IN (1, 9, 21)`.

Janela histórica: `DTACONTA` (entrada). `source_updated_at` permanece COALESCE(DATA, DTACONTA) sem watermark homologado.

## Lacunas documentadas

- Conteúdo XML: **não armazenado no XPERT** — só `COMPENTRADAS.CHAVEACESSONFE` + flag `IMPORTOU_XML` → `xml_imported_in_erp`
- Arquivo XML no Smart Fuel: somente `nfe_xml_documents` + MinIO (Sprint 7.2)
- Frete/seguro/outras: em `COMPENTRADAS` (query de notas com OUTER APPLY)
- Tributos por item (valores): não localizados em ITENSMOVPRODUTOS → NULL
- Unidade no dia 09/07: `UN` → `UNIT_CONVERSION_REQUIRED`
- Títulos: vínculo via NRODOC = NROCOMPROVANTE; sem match → `PENDING_INVOICE_LINK`
- `Entradas NF.txt` usa `ITENSCOMPROVANTE` (camada fiscal) — distinta do movimento de estoque
- Re-sync metadados 09/07: ver `sprint-07-1-resync-invoices-meta.md` (3 notas no dia; overlap 1d puxa 08/07)

## Homologação 2026-07-09 / filial 2443

| Métrica | XPERT / PG |
|---------|------------|
| Notas | 4 |
| Itens | 2 |
| Títulos (janela) | 6 na 2ª sync alinhada |
| Itens aplicados | 2 (EXCLUDED: UN + UNMAPPED) |
| Títulos LINKED | 5 |
| Títulos PENDING_INVOICE_LINK | 8 (acumulado) |
| Idempotência pass 2 | COMPLETED, unchanged |
| Checkpoint incremental | não avançado (janela histórica) |

## Ordem de sync

1. FUEL_PURCHASE_INVOICES  
2. FUEL_PURCHASE_ITEMS  
3. ACCOUNTS_PAYABLE_TITLES  

Item sem cabeçalho → `WAITING_FOR_INVOICE` (staging).  
Título sem nota → `invoice_link_status=PENDING_INVOICE_LINK`.

## Script

`backend/scripts/homolog_sprint71_one_day.py`
