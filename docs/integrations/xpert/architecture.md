# Integração XPERT — Arquitetura

## Fluxo

```
SQL Server 2022 (somente leitura)
        │ pyodbc / ODBC 18
        ▼
DirectSqlServerDataSource
        ▼
XpertSyncService (extração em lotes)
        ▼
erp_staging_records
        ▼
validação + normalização + hash
        ▼
XpertApplyService
        ├── erp_products
        └── erp_suppliers
```

## Processos

- **FastAPI**: cadastro de fontes, enfileiramento de execuções (`QUEUED`, HTTP 202)
- **xpert_sync_worker**: processa fila, agenda e locks
- **PostgreSQL**: fila, staging, checkpoints e destinos

## Abstração

`XpertDataSource` desacopla extração de staging/aplicação. Implementação atual: `DirectSqlServerDataSource`. Futura: `RemoteAgentDataSource` para VPS.

## Regras críticas

1. Zero escrita no SQL Server — validação estática + usuário read-only
2. Credenciais via `secret_ref` (env/arquivo/Docker Secret)
3. Queries versionadas em `backend/app/integrations/xpert/queries/`
4. Staging obrigatório antes de aplicar
5. Mapeamentos manuais preservados (`MAPPED`, `IGNORED`)
6. Checkpoint avança somente após sucesso

Ver também: [security.md](./security.md), [staging.md](./staging.md), [incremental-sync.md](./incremental-sync.md).
