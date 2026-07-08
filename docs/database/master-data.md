# Cadastros mestres — Sprint 2

## Tabelas

| Tabela | Descrição |
|--------|-----------|
| `products` | Produtos canônicos por organização |
| `erp_products` | Produtos originados do XPERT por posto |
| `product_mapping_history` | Histórico de mapeamentos ERP |
| `distributors` | Distribuidoras |
| `erp_suppliers` | Entidades de fornecedor do ERP |
| `distribution_bases` | Bases de carregamento |
| `payment_terms` | Condições de pagamento |
| `station_supplier_rules` | Regras comerciais por posto |
| `master_data_import_jobs` | Jobs de importação CSV |
| `master_data_import_rows` | Linhas processadas por job |

## Chaves e unicidade

- `products`: `(organization_id, code)`
- `erp_products`: `(station_id, erp_product_id)`
- `erp_suppliers`: `(station_id, erp_entity_id)`
- `distributors`: CNPJ único por organização quando informado (índice parcial)
- `distribution_bases`: `(distributor_id, state, normalized_name)`
- `payment_terms`: `(organization_id, code)` e `(organization_id, payment_type, days, normalized_name)`

## Seeds idempotentes

A migration `0003_sprint2_master_data` insere automaticamente para cada organização existente:

**Produtos (6):** ETANOL_HIDRATADO, GASOLINA_C_COMUM, GASOLINA_C_ADITIVADA, DIESEL_B_S10_COMUM, DIESEL_B_S10_ADITIVADO, DIESEL_B_S500_COMUM

**Condições (6):** CASH_0, TERM_7, TERM_15, TERM_21, TERM_30, ANTICIPATED_0

CLI manual:

```bash
docker compose exec backend python -m app.cli seed-master-data --organization-id <UUID>
```

## Migration

```bash
docker compose exec backend alembic upgrade head
```

Revision: `0003_sprint2_master_data` (após `0002_sprint1_identity`).
