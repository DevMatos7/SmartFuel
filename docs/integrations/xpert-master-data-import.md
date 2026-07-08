# Importação manual de cadastros XPERT (CSV)

## Fluxo

1. Upload (`POST /api/v1/master-data-imports/erp-products` ou `erp-suppliers`)
2. Validação e prévia (status `READY`)
3. Confirmação (`POST .../{job_id}/confirm`)
4. Relatório final (`SUCCESS`, `PARTIAL` ou `FAILED`)

## Formatos

### Produtos ERP

```csv
erp_product_id,erp_product_code,erp_description,erp_unit,erp_group_id,erp_group_name,erp_subgroup_id,erp_subgroup_name
```

### Fornecedores ERP

```csv
erp_entity_id,erp_entity_code,erp_name,erp_cnpj
```

O `station_id` é informado no formulário, não no CSV.

## Regras

- Idempotente por chave ERP + posto
- Hash SHA-256 do arquivo registrado
- Limite de tamanho: `MASTER_DATA_IMPORT_MAX_BYTES` (padrão 5 MB)
- Não apaga mapeamentos manuais em reimportação
