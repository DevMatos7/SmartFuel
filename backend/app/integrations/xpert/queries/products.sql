-- PRODUCTS dataset — based on docs/erp/xpert/queries/produtos.sql
-- Parameters: @station_erp_id
-- Inclui inativos: vendas históricas podem referenciar cadastros desativados.
-- Contract aliases required. Validate before enabling dataset.
SELECT
    CAST(PRODUTOS.ID_PRODUTOS AS VARCHAR(100)) AS source_product_id,
    CAST(PRODUTOS.ID_PRODUTOS AS VARCHAR(100)) AS source_product_code,
    PRODUTOS.NOMEPRODUTO AS source_description,
    CAST(NULL AS VARCHAR(30)) AS source_unit,
    CAST(NULL AS VARCHAR(100)) AS source_group_id,
    CAST(NULL AS VARCHAR(150)) AS source_group_name,
    CAST(NULL AS VARCHAR(100)) AS source_subgroup_id,
    CAST(NULL AS VARCHAR(150)) AS source_subgroup_name,
    CAST(NULL AS DATETIME2) AS source_updated_at,
    CAST(PRODUTOS.ATIVO AS BIT) AS source_active
FROM PRODUTOS
WHERE PRODUTOS.ID_FILIAL = @station_erp_id
ORDER BY PRODUTOS.ID_PRODUTOS
