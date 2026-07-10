-- Sprint 6 — contrato pendente de validação com DBA/XPERT.
-- Parâmetros esperados: @station_erp_id, @window_start, @window_end, @batch_limit
SELECT
    CAST(NULL AS VARCHAR(50)) AS source_sale_id,
    CAST(NULL AS VARCHAR(50)) AS source_sale_item_id,
    CAST(NULL AS VARCHAR(50)) AS source_branch_id,
    CAST(NULL AS DATETIME2) AS source_sale_datetime,
    CAST(NULL AS DATE) AS source_business_date,
    CAST(NULL AS VARCHAR(50)) AS source_product_id,
    CAST(NULL AS DECIMAL(18, 6)) AS source_quantity,
    CAST(NULL AS DECIMAL(20, 4)) AS source_net_amount,
    CAST(NULL AS DATETIME2) AS source_updated_at,
    CAST(NULL AS BIT) AS source_cancelled
WHERE 1 = 0;
