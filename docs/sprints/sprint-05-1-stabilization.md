# Sprint 5.1 — Estabilização XPERT

## Objetivo

Tornar o conector executável, seguro e operável antes da Sprint 6.

## Entregas desta estabilização

- Microsoft ODBC Driver 18 na imagem Docker
- Verificação de driver no build (`scripts/verify_odbc.py`)
- Parser T-SQL com sqlglot
- Privilégios efetivos ampliados
- STATIONS com placeholder (sem tabela presumida)
- Invalidação por `query_hash`
- Checkpoint `UNIQUE NULLS NOT DISTINCT` (migration 0010)
- Heartbeat do worker e recuperação de runs abandonadas
- Inativação por ausência somente em `COMPLETED` + modo full
- Telas: fonte, datasets, execuções, detalhe
- Indicadores em Produtos ERP
- Documentação operacional (`security.md`, `operations.md`, `query-contracts.md`, `incremental-sync.md`, `checkpoints.md`, `staging.md`, `vps-migration.md`)
- Indicadores em Produtos ERP e aba ERP de Distribuidores (fornecedores)

## Pendente para homologação real

- Smoke test contra SQL Server de homologação/produção
- Validação formal do DBA para STATIONS
