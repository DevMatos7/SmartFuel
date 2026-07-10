-- SUPPLIERS dataset — based on docs/erp/xpert/queries/entidades.sql
-- Parameters: @station_erp_id
-- Confirm Cliente_Fornecedor filter with DBA before production enablement.
SELECT
    CAST(Entidades.ID_Entidade AS VARCHAR(100)) AS source_supplier_id,
    CAST(Entidades.CODIGOENTIDADE AS VARCHAR(100)) AS source_supplier_code,
    Entidades.NomeEntidade AS source_name,
    Entidades.CnpjCpf AS source_cnpj,
    Entidades.DtaCadastro AS source_updated_at,
    CAST(Entidades.Ativo AS BIT) AS source_active
FROM Entidades
WHERE Entidades.ID_Filial = @station_erp_id
    AND Entidades.Ativo = 1
    AND Cliente_Fornecedor <> 1
ORDER BY Entidades.ID_Entidade
