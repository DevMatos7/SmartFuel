# Sprint 6 — Vendas, volumes, preços praticados e margem

## Status

**Liberada para desenvolvimento e homologação.** Produção bloqueada enquanto a fonte XPERT usar conta `sa`.

## Escopo implementado (parcial)

- Migration `0011` — tabelas analíticas e `security_status` em `erp_sources`
- Datasets `PAYMENT_METHODS`, `FUEL_SALES_ITEMS`, `FUEL_RETAIL_PRICES` com **SQL real** baseada em `faturamento.sql` / `precos_venda.sql`
- Pipeline staging → apply → agregação diária
- Cálculos de preço realizado, custo ERP e margem bruta
- Controles UNSAFE (agenda bloqueada, confirmação manual, bloqueio produção)
- APIs analytics principais e mapeamento de formas de pagamento
- Dashboard React (vendas + qualidade)
- Carga histórica inicial com `history_start_date` / `history_end_date` na sync manual

## Queries SQL

| Dataset | Arquivo | Base |
|---------|---------|------|
| FUEL_SALES_ITEMS | `fuel_sales_items.sql` | `docs/erp/xpert/queries/faturamento.sql` |
| PAYMENT_METHODS | `payment_methods.sql` | Domínio `FORMAPGTO` em faturamento.sql |
| FUEL_RETAIL_PRICES | `fuel_retail_prices.sql` | `docs/erp/xpert/queries/precos_venda.sql` |

Contrato: `docs/integrations/xpert/fuel-sales-contract.md`

## Fonte UNSAFE

Manter `security_status=UNSAFE` com usuário `sa`:

- Sincronização somente manual por ADMIN
- Confirmação explícita na UI
- Agenda automática bloqueada
- `UNSAFE_SOURCE_BLOCKED_IN_PRODUCTION` em `APP_ENV=production`

## Pendências

1. **Validação DBA** — CFOP, coluna de alteração incremental, mapeamento VALOR1..4 ↔ forma de pagamento
2. **Carga histórica 30 dias** — executar manualmente em homologação (SQL pronta)
3. Reconciliação de mapeamentos (`SalesMappingReconciliationService`)
4. APIs faltantes: price-variance, unmapped, missing-cost, quarantined, reconcile-mappings, export PDF
5. Páginas Margens e Preços por forma de pagamento
6. Testes frontend das telas de vendas

## Fórmulas

- Preço médio realizado = valor_líquido / volume_líquido
- Margem bruta = valor_líquido − custo_total_ERP
- Custo ausente → `margin_status=UNAVAILABLE` (nunca zero)
