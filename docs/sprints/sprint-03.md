# Sprint 3 — Central de Cotações Manual, Evidências e Histórico

**Status:** Concluída  
**Dependência:** Sprints 0, 1, 1.1, 2 e estabilizações  
**Migration:** `0005_sprint3_quotes`

## Entregas

### Backend

- 4 tabelas: `quotes`, `quote_items`, `quote_evidences`, `quote_change_history`
- Enums em `app/core/quote_enums.py`
- Services: `QuoteService`, `QuoteEvidenceService`, `QuoteHistoryService`
- Storage MinIO: `app/storage/object_storage.py`
- Router `/api/v1/quotes` (CRUD, itens, evidências, ciclo de vida, histórico, PDF, expiração)
- 11 testes em `tests/test_sprint3_quotes.py`

### Frontend

- Menu **Compras → Cotações**
- `QuotesPage` — listagem, cards, filtros na URL
- `QuoteFormPage` — formulário em etapas
- `QuoteDetailsPage` — abas resumo, itens, evidências, histórico
- `QuoteStatusBadge`
- 1 teste: `QuotesPage.test.tsx`

### Documentação

- `docs/business-rules/quotes.md`
- `docs/business-rules/quote-lifecycle.md`
- `docs/business-rules/quote-items.md`
- `docs/storage/quote-evidences.md`
- `docs/security/evidence-access.md`
- `docs/operations/quote-expiration.md`

## Permissões adicionadas

`quotes.read`, `quotes.write`, `quotes.activate`, `quotes.cancel`, `quotes.revise`, `quotes.duplicate`, `quote_items.write`, `quote_evidences.read`, `quote_evidences.write`, `quote_evidences.deactivate`, `quote_history.read`, `quote_expiration.execute`

## Variáveis de ambiente

```
MINIO_QUOTE_EVIDENCE_BUCKET=quote-evidences
QUOTE_EVIDENCE_MAX_SIZE_MB=10
QUOTE_EXPIRATION_INTERVAL_MINUTES=15
QUOTE_DUPLICATE_WARNING_WINDOW_MINUTES=60
SIGNED_URL_EXPIRE_SECONDS=300
```

## Comandos

```bash
# Migration
docker compose exec backend alembic upgrade head

# Testes
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend sh -c \
  "export DATABASE_URL_SYNC=postgresql+psycopg://smartfuel_test:smartfuel_test@postgres_test:5432/smartfuel_test && alembic upgrade head"
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest tests/ -q
cd frontend && npm run test:run && npm run build

# Expiração manual
curl -X POST http://localhost:8000/api/v1/quotes/expiration/run -H "Authorization: Bearer <token>"
```

## Resultados dos testes (baseline de entrega)

| Suíte | Resultado |
|-------|-----------|
| Backend pytest | 81 passed |
| Frontend Vitest | 37 passed |
| Build frontend | OK |

## Fora do escopo (confirmado)

Ranking, custo equivalente, spread, simulação de compra, economia potencial, integração SQL Server, OCR/IA, automação de portal/WhatsApp.

## Pendências conhecidas

- Cópia de evidências na duplicação (`copy_evidences: true`) — flag aceita, cópia física não implementada
- Scheduler periódico de expiração — endpoint manual; agendamento externo
- Componentes frontend dedicados (dialogs, timeline) — lógica integrada nas pages
- Testes frontend adicionais para formulário, detalhe e fluxos completos

## Decisões técnicas

- Optimistic locking via `version` + `expected_version`
- Status efetivo calculado em runtime
- Revisão cria rascunho; original ativa até ativação da revisão
- Evidências: MinIO com fallback em memória nos testes
- Histórico funcional separado de `audit_log`
- PDF simples via ReportLab (`GET .../export/pdf`)
