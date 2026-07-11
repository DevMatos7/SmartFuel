-- FUEL_PURCHASE_INVOICES — base: entradas_estoque.sql + Entradas NF.txt + COMPENTRADAS
--
-- Hub multi-filial: filtro C.ID_FILIAL = @station_erp_id obrigatório.
-- SAIDAS_ENTRADAS IN (1, 9, 21) conforme entradas de estoque (homologação Sprint 7.1).
-- Cancelados incluídos para correção retroativa.
--
-- COMPENTRADAS (Dados CHAVE XML.txt):
--   CHAVEACESSONFE → source_access_key (44 dígitos)
--   VLRFRETE / VLRSEGURO / VLROUTROS → frete/seguro/outras
--   IMPORTOU_XML → source_xml_imported_in_erp (flag ERP; NÃO é arquivo disponível)
-- O conteúdo XML NÃO está no SQL Server XPERT — ingestão de arquivo fica para Sprint 7.2
--   (diretório/upload externo / MinIO via nfe_xml_documents).
-- OUTER APPLY TOP 1 ... ORDER BY ID_COMPENTRADAS DESC: determinístico se houver >1 COMPENTRADAS.
--
-- source_updated_at: COALESCE(DATA, DTACONTA) — NÃO validado como watermark incremental.
-- Janela histórica: DTACONTA (entrada).
-- Parâmetros: @station_erp_id, @window_start (inclusivo, NULL = sem limite), @window_end (exclusivo)
SELECT
    CAST(C.ID_COMPROVANTE AS VARCHAR(50)) AS source_invoice_id,
    CAST(C.ID_FILIAL AS VARCHAR(50)) AS source_branch_id,
    CAST(C.ID_ENTIDADE AS VARCHAR(50)) AS source_supplier_id,
    CAST(C.NROCOMPROVANTE AS VARCHAR(100)) AS source_document_number,
    CAST(CONVERT(DATE, COALESCE(C.DTAEMISSAO, C.DTACONTA)) AS DATE) AS source_issue_date,
    CAST(CONVERT(DATE, C.DTACONTA) AS DATE) AS source_entry_date,
    CAST(ROUND(C.VLRTOTAL, 4) AS DECIMAL(22, 4)) AS source_total_amount,
    CAST(
        CASE
            WHEN C.CANCELADO = 1 THEN 'CANCELLED'
            ELSE 'ACTIVE'
        END AS VARCHAR(80)
    ) AS source_status,
    CAST(COALESCE(C.DATA, CONVERT(DATETIME2, C.DTACONTA)) AS DATETIME2) AS source_updated_at,
    CAST(C.SERIE AS VARCHAR(20)) AS source_series,
    CAST(
        CASE
            WHEN CE.CHAVEACESSONFE IS NOT NULL
                 AND LEN(LTRIM(RTRIM(CE.CHAVEACESSONFE))) = 44
                 AND CE.CHAVEACESSONFE NOT LIKE '%[^0-9]%'
            THEN LTRIM(RTRIM(CE.CHAVEACESSONFE))
            ELSE NULL
        END AS VARCHAR(44)
    ) AS source_access_key,
    CAST('PURCHASE' AS VARCHAR(40)) AS source_operation_type,
    CAST(ROUND(CAST(ISNULL(CE.VLRFRETE, 0) AS DECIMAL(22, 4)), 4) AS DECIMAL(22, 4)) AS source_freight_amount,
    CAST(ROUND(C.VLRDESCONTO, 4) AS DECIMAL(22, 4)) AS source_discount_amount,
    CAST(ROUND(CAST(ISNULL(CE.VLRSEGURO, 0) AS DECIMAL(22, 4)), 4) AS DECIMAL(22, 4)) AS source_insurance_amount,
    CAST(ROUND(CAST(ISNULL(CE.VLROUTROS, 0) AS DECIMAL(22, 4)), 4) AS DECIMAL(22, 4)) AS source_other_expenses,
    CAST(ROUND(C.VLRICMSTOTAL, 4) AS DECIMAL(22, 4)) AS source_tax_amount,
    CAST(
        CASE
            WHEN CE.IMPORTOU_XML = 1 THEN 1
            ELSE 0
        END AS BIT
    ) AS source_xml_imported_in_erp,
    CAST(
        CASE
            WHEN C.CANCELADO = 1 THEN 1
            ELSE 0
        END AS BIT
    ) AS source_cancelled,
    CAST(NULL AS VARCHAR(100)) AS source_base_id,
    CAST(NULL AS VARCHAR(100)) AS source_payment_condition_id
FROM COMPROVANTES C
OUTER APPLY (
    SELECT TOP 1
        CE.CHAVEACESSONFE,
        CE.VLRFRETE,
        CE.VLRSEGURO,
        CE.VLROUTROS,
        CE.IMPORTOU_XML
    FROM COMPENTRADAS CE
    WHERE CE.ID_COMPROVANTE = C.ID_COMPROVANTE
      AND CE.ID_FILIAL = C.ID_FILIAL
      AND CE.ID_DB = C.ID_DB
    ORDER BY CE.ID_COMPENTRADAS DESC
) CE
WHERE C.ID_FILIAL = @station_erp_id
    AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
    AND (
        @window_start IS NULL
        OR CONVERT(DATETIME2, C.DTACONTA) >= @window_start
    )
    AND CONVERT(DATETIME2, C.DTACONTA) < @window_end
ORDER BY
    C.DTACONTA,
    C.ID_COMPROVANTE;
