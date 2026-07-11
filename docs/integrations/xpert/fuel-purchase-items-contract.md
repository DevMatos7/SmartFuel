# Contrato — FUEL_PURCHASE_ITEMS

Status: **VALID** (homologação filial 2443, Sprint 7.1).

## Objeto XPERT

`ITENSMOVPRODUTOS` + `MOVPRODUTOS` + `COMPROVANTES` + `PRODUTOS`.

Chave: `ID_ITENSMOVPRODUTOS` → `source_invoice_item_id`  
Nota: `ID_COMPROVANTE` → `source_invoice_id`

## Unidade

`PRODUTOS.UNIDADE`. Sem conversão automática de UN/CX/KG.

## Apply

Sem cabeçalho → staging `WAITING_FOR_INVOICE` (não descarta).
