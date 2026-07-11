# Contrato — FUEL_PURCHASE_INVOICES

Status: **VALID** (homologação filial 2443, Sprint 7.1).

## Objeto XPERT

`COMPROVANTES` com `SAIDAS_ENTRADAS IN (1, 9, 21)`.

Chave: `ID_COMPROVANTE` → `source_invoice_id`.

## Janela

Homologação histórica filtra por `DTACONTA` (entrada).

`source_updated_at = COALESCE(DATA, DTACONTA)` — **não** homologado como watermark incremental.

## Campos ausentes (não inventados)

- Conteúdo XML → **não existe no XPERT** (só `COMPENTRADAS.IMPORTOU_XML` → `source_xml_imported_in_erp` + `CHAVEACESSONFE`)
- Frete/seguro/outras → `COMPENTRADAS.VLRFRETE` / `VLRSEGURO` / `VLROUTROS`
- Arquivo XML no Smart Fuel → somente via `nfe_xml_documents` + MinIO (Sprint 7.2)

## Isolamento

`@station_erp_id` obrigatório. Linha de outra filial → `CROSS_STATION_DATA_LEAK`.
