-- FUEL_SALES_ITEMS — base: Faturamento Posto.txt / docs/erp/xpert/queries/faturamento.sql
--
-- IMPORTANTE: esta conexão é hub de replicação (todas as filiais/unidades no mesmo banco).
-- O filtro I.ID_FILIAL = @station_erp_id é obrigatório em toda extração.
--
-- Tabelas: ITENSMOVPRODUTOS, MOVPRODUTOS, COMPROVANTES
-- SAIDAS_ENTRADAS = 0 (saídas/vendas). Cancelados incluídos para correção retroativa.
-- CFOP > '3000' conforme faturamento legado (validar com DBA).
-- Parâmetros: @station_erp_id, @window_start (inclusivo, NULL = sem limite), @window_end (exclusivo)
SELECT
    CAST(M.ID_MOVPRODUTOS AS VARCHAR(50)) AS source_sale_id,
    CAST(I.ID_ITENSMOVPRODUTOS AS VARCHAR(50)) AS source_sale_item_id,
    CAST(I.ID_FILIAL AS VARCHAR(50)) AS source_branch_id,
    CAST(M.DATA AS DATETIME2) AS source_sale_datetime,
    CAST(COALESCE(CONVERT(DATE, M.DATA), C.DTACONTA) AS DATE) AS source_business_date,
    CAST(I.ID_PRODUTOS AS VARCHAR(50)) AS source_product_id,
    CAST(ROUND(I.QTDE, 6) AS DECIMAL(18, 6)) AS source_quantity,
    CAST(ROUND(I.TOTAL, 4) AS DECIMAL(20, 4)) AS source_net_amount,
    CAST(COALESCE(M.DATA, CONVERT(DATETIME2, C.DTACONTA)) AS DATETIME2) AS source_updated_at,
    CAST(
        CASE
            WHEN C.CANCELADO = 1 OR I.STATUS = 2 THEN 1
            ELSE 0
        END AS BIT
    ) AS source_cancelled,
    CAST(C.NROCOMPROVANTE AS VARCHAR(100)) AS source_document_number,
    CAST(NULL AS VARCHAR(30)) AS source_unit,
    CAST(ROUND(I.PRECO_BASE_VENDA, 8) AS DECIMAL(18, 8)) AS source_unit_price,
    CAST(ROUND(I.QTDE * I.PRECO_BASE_VENDA, 4) AS DECIMAL(20, 4)) AS source_gross_amount,
    CAST(ROUND(I.VLRDESCONTO, 4) AS DECIMAL(20, 4)) AS source_discount_amount,
    CAST(NULL AS DECIMAL(20, 4)) AS source_surcharge_amount,
    CAST(ROUND(I.VLRCUSTO, 8) AS DECIMAL(18, 8)) AS source_cost_per_unit,
    CAST(ROUND(I.QTDE * I.VLRCUSTO, 4) AS DECIMAL(20, 4)) AS source_total_cost,
    CAST(I.CFOP AS VARCHAR(20)) AS source_cfop,
    CAST(M.FORMAPGTO AS VARCHAR(50)) AS source_payment_method_id,
    CAST(
        CASE
            WHEN I.QTDE < 0 THEN 'RETURN'
            ELSE 'SALE'
        END AS VARCHAR(30)
    ) AS source_operation_type
FROM ITENSMOVPRODUTOS I
INNER JOIN MOVPRODUTOS M
    ON I.ID_MOVPRODUTOS = M.ID_MOVPRODUTOS
    AND I.ID_FILIAL = M.ID_FILIAL
    AND I.ID_DB = M.ID_DB
INNER JOIN COMPROVANTES C
    ON C.ID_COMPROVANTE = M.ID_COMPROVANTE
    AND C.ID_FILIAL = M.ID_FILIAL
    AND C.ID_DB = M.ID_DB
INNER JOIN PRODUTOS P
    ON P.ID_PRODUTOS = I.ID_PRODUTOS
    AND P.ID_FILIAL = I.ID_FILIAL
WHERE I.ID_FILIAL = @station_erp_id
    AND M.ID_FILIAL = @station_erp_id
    AND C.ID_FILIAL = @station_erp_id
    AND C.SAIDAS_ENTRADAS = 0
    AND I.CFOP > '3000'
    AND (
        @window_start IS NULL
        OR COALESCE(M.DATA, CONVERT(DATETIME2, C.DTACONTA)) >= @window_start
    )
    AND COALESCE(M.DATA, CONVERT(DATETIME2, C.DTACONTA)) < @window_end
ORDER BY
    COALESCE(M.DATA, CONVERT(DATETIME2, C.DTACONTA)),
    I.ID_ITENSMOVPRODUTOS;
