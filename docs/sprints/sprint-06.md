# Sprint 6 — Vendas, volumes, preços praticados e margem

## Status

**Liberada para desenvolvimento e homologação.** Produção bloqueada enquanto a fonte XPERT usar conta `sa`.

## Escopo implementado (parcial)

- Migration `0011` — tabelas analíticas e `security_status` em `erp_sources`
- Datasets `PAYMENT_METHODS`, `FUEL_SALES_ITEMS`, `FUEL_RETAIL_PRICES` (SQL stub até validação DBA)
- Pipeline staging → apply → agregação diária
- Cálculos de preço realizado, custo ERP e margem bruta
- Controles UNSAFE (agenda bloqueada, confirmação manual, bloqueio produção)
- APIs analytics principais e mapeamento de formas de pagamento
- Dashboard React (vendas + qualidade)

## Fonte UNSAFE

Manter `security_status=UNSAFE` com usuário `sa`:

- Sincronização somente manual por ADMIN
- Confirmação explícita na UI
- Agenda automática bloqueada
- `UNSAFE_SOURCE_BLOCKED_IN_PRODUCTION` em `APP_ENV=production`

## Pendências

1. SQL real validado para vendas/preços/pagamentos (RDC-002)
2. Carga histórica 30 dias em homologação
3. Reconciliação de mapeamentos (`SalesMappingReconciliationService`)
4. Exportação PDF executiva
5. Páginas Margens e Preços por forma de pagamento (estrutura inicial no menu)
6. Testes de integração com SQL Server real

## Fórmulas

- Preço médio realizado = valor_líquido / volume_líquido
- Margem bruta = valor_líquido − custo_total_ERP
- Custo ausente → `margin_status=UNAVAILABLE` (nunca zero)

Ver também: `docs/erp/xpert/queries/faturamento.sql` como referência de vendas XPERT.
