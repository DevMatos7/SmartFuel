# Workflow de aprovação

Estados principais: `DRAFT` → `PENDING_APPROVAL` → `APPROVED_PENDING_IMPLEMENTATION` → `IMPLEMENTED_*` (ou `REJECTED` / `CANCELLED` / `EXPIRED`).

- Autoaprovação bloqueável (`allow_self_approval=false`).
- Múltiplos níveis; mesmo usuário não aprova dois níveis.
- Evidências imutáveis (MinIO + metadados).
- Toda transição é auditada.
