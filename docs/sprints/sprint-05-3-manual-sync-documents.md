# Sprint 5.3 — Operação manual e documentos de fornecedores

## Entregas

### Tratamento INVALID_CNPJ
- `app/utils/brazilian_document.py` — classificação CNPJ/CPF/vazio/inválido
- CNPJ vazio → aplicado sem quarentena
- CPF válido (11 dígitos) → aplicado com `erp_cpf` no payload normalizado
- CNPJ preenchido e inválido → quarentena `INVALID_CNPJ` com `reason` no erro
- Endpoint `GET /sync-runs/{id}/supplier-document-diagnostics` — agrupamento por motivo

### UI
- `/integrations/xpert/sync` — sincronização manual com confirmação de full
- Lista de execuções com paginação, filtros, ordenação e polling condicional

### Testes
- Backend: `test_brazilian_document.py`, `test_xpert_supplier_documents.py`
- Frontend: `XpertManualSyncPage.test.tsx`, `XpertSyncRunsPage.test.tsx`, `XpertSyncRunDetailsPage.test.tsx`

## Próximo passo operacional

Reexecutar full de SUPPLIERS após o deploy para:
1. Aplicar fornecedores com CPF ou sem documento (antes em quarentena)
2. Obter `COMPLETED` e destravar checkpoint incremental
3. Validar diagnóstico via API de documentos na run

```bash
# UI: Integração XPERT → Sincronizar → SUPPLIERS → posto 2443 → FULL_SNAPSHOT_HASH

# Diagnóstico pós-execução
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/integrations/xpert/sync-runs/{run_id}/supplier-document-diagnostics"
```
