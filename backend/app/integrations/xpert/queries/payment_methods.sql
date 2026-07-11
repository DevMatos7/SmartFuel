-- PAYMENT_METHODS — domínio MOVPRODUTOS.FORMAPGTO documentado em faturamento.sql
-- Snapshot estático dos códigos observados no ERP (sem tabela dedicada confirmada).
SELECT
    pm.source_payment_method_id,
    pm.source_payment_method_code,
    pm.source_payment_method_name,
    CAST(1 AS BIT) AS source_active,
    CAST(NULL AS DATETIME2) AS source_updated_at
FROM (
    SELECT CAST('0' AS VARCHAR(50)) AS source_payment_method_id, CAST('0' AS VARCHAR(50)) AS source_payment_method_code, CAST('Dinheiro' AS VARCHAR(255)) AS source_payment_method_name
    UNION ALL SELECT '1', '1', 'à Prazo'
    UNION ALL SELECT '2', '2', 'Chq Pre-Dta'
    UNION ALL SELECT '3', '3', 'Convênio C/C'
    UNION ALL SELECT '4', '4', 'Cartão Débito'
    UNION ALL SELECT '5', '5', 'Carta Frete'
    UNION ALL SELECT '6', '6', 'Dep. Bancário'
    UNION ALL SELECT '7', '7', 'Chq Vista'
    UNION ALL SELECT '8', '8', 'Moedas Div.'
    UNION ALL SELECT '9', '9', 'Outras'
    UNION ALL SELECT '16', '16', 'Cartão Fidelidade'
) pm;
