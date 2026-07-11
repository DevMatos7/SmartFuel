-- ACCOUNTS_PAYABLE_TITLES — base: docs/erp/xpert/queries/contas_pagar.sql
--
-- Hub multi-filial: filtro CP.ID_FILIAL = @station_erp_id obrigatório.
-- Inclui títulos liquidados (sem filtro DTAPGTO IS NULL) para correção retroativa.
-- Vínculo com nota: LEFT JOIN COMPROVANTES por filial + entidade + NRODOC = NROCOMPROVANTE.
-- Quando o join não encontrar nota: source_invoice_id = NRODOC (documento) e link posterior.
-- source_updated_at: COALESCE(DTAPGTO, DTAVCTO, DTACONTA) — NÃO validado como watermark.
-- Parâmetros: @station_erp_id, @window_start (inclusivo, NULL = sem limite), @window_end (exclusivo)
SELECT
    CAST(CP.ID_CONTASPAGAR AS VARCHAR(50)) AS source_title_id,
    CAST(CP.ID_FILIAL AS VARCHAR(50)) AS source_branch_id,
    CAST(ISNULL(CP.ID_ENTIDADE, 0) AS VARCHAR(50)) AS source_supplier_id,
    CAST(
        COALESCE(
            CAST(C.ID_COMPROVANTE AS VARCHAR(50)),
            CAST(CP.NRODOC AS VARCHAR(50))
        ) AS VARCHAR(100)
    ) AS source_invoice_id,
    CAST(CONVERT(DATE, CP.DTAVCTO) AS DATE) AS source_due_date,
    CAST(ROUND(CP.VALOR, 4) AS DECIMAL(22, 4)) AS source_original_amount,
    CAST(
        ROUND(
            CP.VALOR - ISNULL((
                SELECT SUM(ISNULL(CPB.VALORBAIXA, 0))
                FROM CONTASPAGARBAIXA CPB
                WHERE CPB.ID_FILIAL = CP.ID_FILIAL
                  AND CPB.ID_CONTASPAGAR = CP.ID_CONTASPAGAR
            ), 0),
            4
        ) AS DECIMAL(22, 4)
    ) AS source_open_amount,
    CAST(
        CASE
            WHEN CP.DTAPGTO IS NOT NULL
                 AND (
                     CP.VALOR - ISNULL((
                         SELECT SUM(ISNULL(CPB.VALORBAIXA, 0))
                         FROM CONTASPAGARBAIXA CPB
                         WHERE CPB.ID_FILIAL = CP.ID_FILIAL
                           AND CPB.ID_CONTASPAGAR = CP.ID_CONTASPAGAR
                     ), 0)
                 ) <= 0
            THEN 'PAID'
            WHEN ISNULL((
                     SELECT SUM(ISNULL(CPB.VALORBAIXA, 0))
                     FROM CONTASPAGARBAIXA CPB
                     WHERE CPB.ID_FILIAL = CP.ID_FILIAL
                       AND CPB.ID_CONTASPAGAR = CP.ID_CONTASPAGAR
                 ), 0) > 0
            THEN 'PARTIALLY_PAID'
            WHEN CP.DTAVCTO < CAST(GETDATE() AS DATE) THEN 'OVERDUE'
            ELSE 'OPEN'
        END AS VARCHAR(80)
    ) AS source_status,
    CAST(
        COALESCE(
            CONVERT(DATETIME2, CP.DTAPGTO),
            CONVERT(DATETIME2, CP.DTAVCTO),
            CONVERT(DATETIME2, CP.DTACONTA)
        ) AS DATETIME2
    ) AS source_updated_at,
    CAST(NULL AS INT) AS source_installment_number,
    CAST(CP.NRODOC AS VARCHAR(100)) AS source_document_number,
    CAST(CONVERT(DATE, CP.DTACONTA) AS DATE) AS source_issue_date,
    CAST(CONVERT(DATE, CP.DTAPGTO) AS DATE) AS source_payment_date,
    CAST(
        ROUND(
            ISNULL((
                SELECT SUM(ISNULL(CPB.VALORBAIXA, 0))
                FROM CONTASPAGARBAIXA CPB
                WHERE CPB.ID_FILIAL = CP.ID_FILIAL
                  AND CPB.ID_CONTASPAGAR = CP.ID_CONTASPAGAR
            ), 0),
            4
        ) AS DECIMAL(22, 4)
    ) AS source_paid_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_interest_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_penalty_amount,
    CAST(NULL AS DECIMAL(22, 4)) AS source_discount_amount,
    CAST(NULL AS VARCHAR(100)) AS source_bank_or_wallet,
    CAST(NULL AS VARCHAR(80)) AS source_payment_method,
    CAST(0 AS BIT) AS source_cancelled
FROM CONTASPAGAR CP
OUTER APPLY (
    SELECT TOP 1 C2.ID_COMPROVANTE
    FROM COMPROVANTES C2
    WHERE C2.ID_FILIAL = CP.ID_FILIAL
      AND C2.ID_ENTIDADE = CP.ID_ENTIDADE
      AND C2.NROCOMPROVANTE = CP.NRODOC
      AND C2.SAIDAS_ENTRADAS IN (1, 9, 21)
    ORDER BY C2.ID_COMPROVANTE
) C
WHERE CP.ID_FILIAL = @station_erp_id
    AND (
        @window_start IS NULL
        OR CONVERT(DATETIME2, CP.DTACONTA) >= @window_start
    )
    AND CONVERT(DATETIME2, CP.DTACONTA) < @window_end
ORDER BY
    CP.DTAVCTO,
    CP.ID_CONTASPAGAR;
