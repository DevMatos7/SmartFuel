# Sprint 3.1 — Estabilização da Central de Cotações

**Status:** Concluída  
**Dependência:** Sprint 3  
**Migration:** `0006_sprint31_quotes`

## Correções entregues

### Scheduler e expiração

- Serviço Docker `quote_scheduler` com loop assíncrono.
- `QuoteExpirationService` com advisory lock PostgreSQL.
- Expiração idempotente com histórico e auditoria.
- Endpoint manual mantido para ADMIN.

### Validade por item

- `item_effective_status` e `effective_valid_until` nas respostas.
- Cotação efetivamente expirada quando validade geral vence ou todos os itens vencem.
- Item isolado expirado não invalida cotação com outros itens ativos.

### Duplicação

- `copy_evidences: true` com cópia física no MinIO.
- Campo `source_evidence_id` na evidência copiada.
- Interface `QuoteDuplicateDialog` no detalhe da cotação.
- Correção de `MissingGreenlet` na cópia de itens.

### Numeração segura

- Tabela `organization_quote_counters`.
- Alocação via `INSERT ... ON CONFLICT DO UPDATE RETURNING`.
- Backfill a partir de `MAX(quote_number)` na migration.

### Storage

- `OBJECT_STORAGE_ALLOW_MEMORY_FALLBACK` (padrão `false` em produção).
- Compensação: remove objeto se metadados falharem.
- `delete_object` e `copy_object` no `ObjectStorageService`.

### Interface

- `QuoteDuplicateDialog`, `QuoteRevisionDialog`, `QuoteActivationDialog`, `QuoteCancelDialog`.
- Status por item na aba Itens do detalhe.

### Testes

- `test_sprint31_stabilization.py` — 9 testes novos.
- `QuoteDetailsPage.test.tsx`, `QuoteDialogs.test.tsx`.

## Resultados

| Suíte | Resultado |
|-------|-----------|
| Backend pytest | 90 passed |
| Frontend Vitest | 42 passed |
| Build frontend | OK |

## Documentação

- `docs/operations/quote-scheduler.md`
- `docs/storage/evidence-copy-and-compensation.md`
- Atualizações em `quote-expiration.md`, `quotes.md`, `quote-lifecycle.md`

## Confirmação Sprint 4

Nenhuma funcionalidade de ranking, custo equivalente ou spread foi implementada.
