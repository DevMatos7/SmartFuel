# Contratos de consulta XPERT

## Princípio

Cada dataset possui um contrato que define colunas obrigatórias, aliases esperados, tipos e regras de validação. O contrato só pode ser marcado como `VALID` após execução controlada contra a origem real.

## Datasets

### PRODUCTS (`products.sql`)

| Alias | Obrigatório | Tipo esperado | Descrição |
|-------|-------------|---------------|-----------|
| `source_product_id` | Sim | string/int | Chave natural na origem |
| `source_description` | Sim | string | Descrição do produto |
| `source_updated_at` | Incremental | datetime | Última alteração na origem |
| `source_active` | Opcional | bool/int | Indicador de ativo |

Campos opcionais: código ERP, unidade, grupo, subgrupo.

### SUPPLIERS (`suppliers.sql`)

| Alias | Obrigatório | Tipo esperado | Descrição |
|-------|-------------|---------------|-----------|
| `source_supplier_id` | Sim | string/int | Chave natural |
| `source_name` | Sim | string | Razão ou nome |
| `source_updated_at` | Incremental | datetime | Última alteração |
| CNPJ e demais | Opcional | string | Normalizados no staging |

### STATIONS

**Desabilitado** (`MISCONFIGURED`). Não existe contrato operacional até confirmação formal do DBA sobre tabelas e colunas.

### FUEL_PURCHASE_INVOICES / FUEL_PURCHASE_ITEMS / ACCOUNTS_PAYABLE_TITLES (Sprint 7)

Status: **MISCONFIGURED** até SQL real validado com o DBA.

Placeholders:

- `fuel_purchase_invoices.sql`
- `fuel_purchase_items.sql`
- `accounts_payable_titles.sql`

Contratos detalhados:

- [fuel-purchase-invoices-contract.md](./fuel-purchase-invoices-contract.md)
- [fuel-purchase-items-contract.md](./fuel-purchase-items-contract.md)
- [accounts-payable-contract.md](./accounts-payable-contract.md)

Parâmetros obrigatórios (quando houver SQL real): `@station_erp_id`, `@window_start`, `@window_end`.

## Validação

1. Parser T-SQL confirma somente leitura.
2. Execução com `LIMIT` reduzido na homologação.
3. Verificação de aliases, tipos, nulos e duplicidade de chave.
4. `query_hash` do arquivo é persistido no dataset.
5. Alteração posterior do SQL invalida o contrato (`PENDING_VALIDATION`).

## Duplicidade

Chave natural duplicada na amostra bloqueia habilitação da agenda até correção da consulta ou tratamento acordado com o DBA.

## Referências

- Queries versionadas: `backend/app/integrations/xpert/queries/`
- Serviço: `xpert_source_service.validate_contract()`
