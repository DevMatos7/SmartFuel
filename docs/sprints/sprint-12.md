# Sprint 12 — Centro executivo, alertas, observabilidade e hardening

**Status:** Fundação + homologação sintética liberadas.

**Proibições:** escrita XPERT · scheduler com `sa` · produção com `sa` · Sprint 13.

## Entregue

- Migration `0023_sprint12_ops_hardening`
- Dashboard executivo `/executive` (KPI com qualidade/freshness; ausência ≠ zero)
- Motor de alertas + lifecycle + deduplicação
- Outbox, health/ready/dependencies, SLO placeholders, incidentes, feature flags, readiness
- Correlation ID (`X-Correlation-ID`)
- Docs operations/security/runbooks

## Prontidão

Enquanto XPERT usar `sa` → `NOT_READY`.

## Confirmações

- XPERT somente leitura
- Produção com sa bloqueada
- Sprint 13 não antecipada
