# Contrato — ACCOUNTS_PAYABLE_TITLES

Status: **VALID** (homologação filial 2443, Sprint 7.1).

## Objeto XPERT

`CONTASPAGAR` + baixas em `CONTASPAGARBAIXA`.

Chave: `ID_CONTASPAGAR` → `source_title_id`

Vínculo com nota: `OUTER APPLY` em `COMPROVANTES` por filial + entidade + `NRODOC = NROCOMPROVANTE`.

Sem match: `source_invoice_id = NRODOC` e `invoice_link_status = PENDING_INVOICE_LINK`.

## Janela

`DTACONTA` do título.
