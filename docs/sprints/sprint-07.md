# Sprint 7 — Compras de combustíveis, NF-e de entrada e contas a pagar

## Status

| Item | Estado |
|------|--------|
| Sprint 7 fundação | APROVADA |
| Sprint 7.1 contratos + apply + 1 dia | EXECUTADA |
| XML | ADIADO PARA 7.2 |
| Fonte XPERT | UNSAFE — usuário `sa` |
| Agenda automática | BLOQUEADA |
| Produção com `sa` | BLOQUEADA |
| Sprint 6 | PERMANECE ABERTA (incremental + formas de pagamento) |
| Sprint 8 | NÃO AUTORIZADA |

Ver também: [sprint-07-1-contracts-apply-one-day.md](./sprint-07-1-contracts-apply-one-day.md)

## Escopo

Datasets:

- `FUEL_PURCHASE_INVOICES` (MISCONFIGURED até SQL real)
- `FUEL_PURCHASE_ITEMS` (MISCONFIGURED até SQL real)
- `ACCOUNTS_PAYABLE_TITLES` (MISCONFIGURED até SQL real)
- `NFE_XML_DOCUMENTS` (ingestão via abstração `NfeXmlSource`, não via SQL inventado)

Tabelas PostgreSQL (migration `0015_sprint7_purchases`):

- `fuel_purchase_invoices`
- `fuel_purchase_items`
- `nfe_xml_documents`
- `accounts_payable_titles`
- `fuel_purchase_daily_metrics`

## Controles UNSAFE

- `security_status=UNSAFE`
- `XPERT_ALLOW_UNSAFE_PRIVILEGES=true`
- `APP_ENV` ≠ production
- Execução manual por ADMIN
- Confirmação textual: `CONFIRMAR HOMOLOGAÇÃO DE COMPRAS XPERT`
- Scheduler bloqueado
- Sem escrita no XPERT

## Queries

Placeholders em:

- `backend/app/integrations/xpert/queries/fuel_purchase_invoices.sql`
- `backend/app/integrations/xpert/queries/fuel_purchase_items.sql`
- `backend/app/integrations/xpert/queries/accounts_payable_titles.sql`

Referências exploratórias (não contratuais):

- `docs/erp/xpert/queries/entradas_estoque.sql`
- `docs/erp/xpert/queries/contas_pagar.sql`

## Fora de escopo (Sprint 8)

- Comparação compra × cotação
- Economia potencial
- Índice de escolha da distribuidora

## Homologação planejada

1. Validar contratos reais com DBA
2. Um dia → sete dias → trinta dias
3. Reexecução idempotente
4. XML seguro + reconciliação ERP × XML

## Pendências

- SQL real dos três datasets (sair de MISCONFIGURED)
- Identificar origem física do XML no ambiente
- Apply completo + agregação diária em produção de sync
- Exportações CSV/PDF
- Import/reconcile NF-e via API POST
- Sprint 6: incremental `source_updated_at` e formas de pagamento
