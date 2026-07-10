-- STATIONS dataset — MISCONFIGURED até validação formal do DBA.
-- Não executar contra o XPERT. Placeholder somente leitura sem tabelas presumidas.
SELECT
    CAST(NULL AS VARCHAR(100)) AS source_branch_id,
    CAST(NULL AS VARCHAR(255)) AS source_trade_name,
    CAST(NULL AS VARCHAR(14)) AS source_cnpj,
    CAST(NULL AS BIT) AS source_active
WHERE 1 = 0
