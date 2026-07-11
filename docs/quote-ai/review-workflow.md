# Workflow de revisão

## Estados do documento

`UPLOADED` → `AI_EXTRACTION` → `NEEDS_REVIEW` → (`READY_FOR_DRAFT` | `REJECTED` | `FAILED`) → `DRAFT_CREATED`

## Estados da review

`PENDING` → `IN_REVIEW` → `APPROVED` | `APPROVED_WITH_CORRECTIONS` | `REJECTED`

## API

| Ação | Endpoint |
|------|----------|
| Iniciar | `POST /documents/{id}/start-review` |
| Salvar correções | `PUT /documents/{id}/review` |
| Aprovar | `POST /documents/{id}/approve` |
| Rejeitar | `POST /documents/{id}/reject` |
| Criar rascunho | `POST /documents/{id}/create-draft` |

UI: `/quotes/ai/documents/:documentId`.

## Regras

1. Revisão humana obrigatória (`human_review_required=true`)
2. Create-draft só após approve
3. Quote criada com `origin=AI_ASSISTED_INGESTION`, `analytics_eligible=false`, status rascunho
4. `activated=false` sempre na resposta — ativação só na Central de Cotações
5. Um draft link por documento
