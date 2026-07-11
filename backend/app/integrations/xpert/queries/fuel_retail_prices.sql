-- FUEL_RETAIL_PRICES — base: Preço de venda.txt / docs/erp/xpert/queries/precos_venda.sql
--
-- Hub de replicação: filtrar sempre por ID_FILIAL = @station_erp_id.
-- Mapeamento provisório VALORn → FORMAPGTO (confirmar com operação/DBA):
--   VALOR1 → 0 (Dinheiro)
--   VALOR2 → 4 (Cartão Débito)
--   VALOR3 → 1 (à Prazo)
--   VALOR4 → 3 (Convênio C/C)
SELECT
    CAST(PPLV.ID_FILIAL AS VARCHAR(50)) AS source_branch_id,
    CAST(PPLV.ID_PRODUTOS AS VARCHAR(50)) AS source_product_id,
    CAST(prices.source_payment_method_id AS VARCHAR(50)) AS source_payment_method_id,
    CAST(ROUND(prices.source_price_per_liter, 8) AS DECIMAL(18, 8)) AS source_price_per_liter,
    CAST(PPLV.ATIVO AS BIT) AS source_active,
    CAST(NULL AS DATETIME2) AS source_effective_from,
    CAST(NULL AS DATETIME2) AS source_effective_until,
    CAST(NULL AS DATETIME2) AS source_updated_at
FROM PRODUTOSPORLOCALVENDA PPLV
INNER JOIN PRODUTOS P
    ON P.ID_PRODUTOS = PPLV.ID_PRODUTOS
    AND P.ID_FILIAL = PPLV.ID_FILIAL
CROSS APPLY (
    SELECT CAST('0' AS VARCHAR(50)) AS source_payment_method_id, PPLV.VALOR1 AS source_price_per_liter
    UNION ALL SELECT '4', PPLV.VALOR2
    UNION ALL SELECT '1', PPLV.VALOR3
    UNION ALL SELECT '3', PPLV.VALOR4
) prices
WHERE PPLV.ID_FILIAL = @station_erp_id
    AND PPLV.ATIVO = 1
    AND P.ATIVO = 1
    AND prices.source_price_per_liter IS NOT NULL
    AND prices.source_price_per_liter > 0;
