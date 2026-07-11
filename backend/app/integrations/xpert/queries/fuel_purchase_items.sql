-- FUEL_PURCHASE_ITEMS — base: docs/erp/xpert/queries/entradas_estoque.sql
--
-- Hub multi-filial: filtro I.ID_FILIAL = @station_erp_id obrigatório.
-- Granularidade: uma linha por ID_ITENSMOVPRODUTOS.
-- Unidade: PRODUTOS.UNIDADE (não inventar conversão).
-- Frete/seguro/outras por item: não localizados — NULL (rateio só se cabeçalho informar).
-- Tributos detalhados por item: valores ICMS/PIS/COFINS não localizados — NULL.
-- source_updated_at: COALESCE(M.DATA, C.DTACONTA) — NÃO validado como watermark incremental.
-- Parâmetros: @station_erp_id, @window_start (inclusivo, NULL = sem limite), @window_end (exclusivo)
SELECT
    CAST(C.ID_COMPROVANTE AS VARCHAR(50)) AS source_invoice_id,
    CAST(I.ID_ITENSMOVPRODUTOS AS VARCHAR(50)) AS source_invoice_item_id,
    CAST(I.ID_FILIAL AS VARCHAR(50)) AS source_branch_id,
    CAST(C.ID_ENTIDADE AS VARCHAR(50)) AS source_supplier_id,
    CAST(I.ID_PRODUTOS AS VARCHAR(50)) AS source_product_id,
    CAST(ROUND(I.QTDE, 6) AS DECIMAL(20, 6)) AS source_quantity,
    CAST(P.UNIDADE AS VARCHAR(30)) AS source_unit,
    CAST(ROUND(I.VLRUNITARIO, 8) AS DECIMAL(20, 8)) AS source_unit_price,
    CAST(
        ROUND(
            CASE
                WHEN I.VLRCUSTOSEMICMS = 0 THEN I.TOTAL
                ELSE (I.QTDE * I.VLRCUSTOSEMICMS)
            END,
            4
        ) AS DECIMAL(22, 4)
    ) AS source_item_total,
    CAST(COALESCE(M.DATA, CONVERT(DATETIME2, C.DTACONTA)) AS DATETIME2) AS source_updated_at,
    CAST(P.NOMEPRODUTO AS VARCHAR(255)) AS source_product_description,
    CAST(I.CFOP AS VARCHAR(20)) AS source_cfop,
    CAST(P.NCM AS VARCHAR(20)) AS source_ncm,
    CAST(ROUND(I.VLRDESCONTO, 4) AS DECIMAL(22, 4)) AS source_discount_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_freight_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_insurance_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_other_expenses,
    CAST(NULL AS DECIMAL(22, 4)) AS source_icms_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_icms_st_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_fcp_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_pis_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_cofins_amount,
    CAST(
        ROUND(
            CASE
                WHEN I.VLRCUSTOSEMICMS = 0 THEN I.TOTAL
                ELSE (I.QTDE * I.VLRCUSTOSEMICMS)
            END,
            4
        ) AS DECIMAL(22, 4)
    ) AS source_total_cost,
    CAST(
        ROUND(
            CASE
                WHEN I.VLRCUSTOSEMICMS = 0 THEN I.VLRUNITARIO
                ELSE I.VLRCUSTOSEMICMS
            END,
            8
        ) AS DECIMAL(20, 8)
    ) AS source_cost_per_unit,
    CAST(
        CASE
            WHEN C.CANCELADO = 1 OR I.STATUS = 2 THEN 1
            ELSE 0
        END AS BIT
    ) AS source_cancelled,
    CAST(
        CASE
            WHEN I.QTDE < 0 THEN 'PURCHASE_RETURN'
            ELSE 'PURCHASE'
        END AS VARCHAR(40)
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
    AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
    AND (
        @window_start IS NULL
        OR CONVERT(DATETIME2, C.DTACONTA) >= @window_start
    )
    AND CONVERT(DATETIME2, C.DTACONTA) < @window_end
ORDER BY
    C.DTACONTA,
    I.ID_ITENSMOVPRODUTOS;
