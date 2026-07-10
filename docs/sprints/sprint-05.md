# Sprint 5 — Conector XPERT

## Entregue

- Modelos: `erp_sources`, `erp_datasets`, `erp_sync_checkpoints`, `erp_sync_runs`, `erp_staging_records`, `erp_sync_errors`
- Migration `0009_sprint5_xpert`
- Conector `DirectSqlServerDataSource` (pyodbc)
- Validador SQL somente leitura
- Contratos PRODUCTS / SUPPLIERS / STATIONS
- Staging, hash, aplicação idempotente
- Worker `xpert_sync_worker`
- API `/api/v1/integrations/xpert/*`
- Permissões `erp_integration.*` e `erp_sync.*`
- UI dashboard básico em `/integrations/xpert`
- 10 testes backend novos (133 total)

## Pendências operacionais

- Instalar **ODBC Driver 18** na imagem Docker de produção (pyodbc já incluído)
- Validar consulta `stations.sql` com DBA (tabela `Filiais`)
- Configurar credencial SQL somente leitura e `secret_ref` no ambiente
- Habilitar datasets após validação de contrato com SQL Server real

## Sprint 6

Não antecipada: vendas, compras, estoque, NF-e permanecem fora do escopo.
