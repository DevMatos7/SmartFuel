# Operações — Integração XPERT

## Pré-requisitos

1. ODBC Driver 18 instalado no container (`python scripts/verify_odbc.py`)
2. `secret_ref` configurado
3. Conta SQL somente leitura
4. `erp_branch_id` nos postos

## Primeira sincronização

1. Cadastrar fonte em `/integrations/xpert/source`
2. Testar conexão
3. Validar contrato PRODUCTS e SUPPLIERS
4. Executar `FULL_SNAPSHOT_HASH` para um posto
5. Conferir staging e fila de mapeamento

## Incremental

- Janela: `[checkpoint - overlap, source_upper_bound)`
- `source_upper_bound` vem de `SYSUTCDATETIME()` no SQL Server
- Checkpoint avança somente em `COMPLETED`

## Falhas

| Situação | Ação |
|----------|------|
| `PARTIAL` | Corrigir linhas em quarentena; reexecutar (checkpoint mantido) |
| `FAILED_WORKER_LOST` | Retry manual; verificar worker |
| `QUERY_CHANGED_AFTER_VALIDATION` | Revalidar contrato |
| STATIONS | Permanece `MISCONFIGURED` até DBA |

## Reset de checkpoint

Somente ADMIN, com motivo e confirmação. Reprocessa janela completa.

## Precificação (Sprint 11)

A formação de preço **não escreve** no XPERT. Preços aprovados são implantados externamente e conferidos via confirmação manual ou snapshot ERP posterior.

