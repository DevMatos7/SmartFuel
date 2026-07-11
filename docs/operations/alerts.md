# Alertas

Motor com deduplicação (`deduplication_key`), cooldown, auto-resolve e lifecycle.

`UNSAFE_XPERT_SOURCE` é CRITICAL, `dismissible=false` — reconhecível, não resolvível enquanto `sa` estiver ativo.

Alertas devem ser acionáveis (o quê, onde, impacto, evidência, deep link).

## Sprint 13 — Quote AI

| Código | Severidade típica | Quando |
|--------|-------------------|--------|
| `QUOTE_AI_PROCESSING_FAILED` | HIGH | Falha no pipeline de extração |
| `QUOTE_AI_PROVIDER_UNAVAILABLE` | HIGH | Provedor indisponível |
| `QUOTE_AI_BUDGET_EXCEEDED` | HIGH | Limite de custo estourado |
| `QUOTE_AI_LOW_CONFIDENCE` | WARNING | `document_confidence` &lt; 0.70 |
| `QUOTE_AI_REVIEW_OVERDUE` | WARNING | Revisão pendente além do prazo |
| `QUOTE_AI_DUPLICATE_DOCUMENT` | INFO/WARNING | SHA-256 já existente na org |
| `QUOTE_AI_PROMPT_INJECTION_DETECTED` | HIGH | Padrão de injection no texto |
| `QUOTE_AI_HIGH_CORRECTION_RATE` | WARNING | Taxa alta de correções humanas |
| `QUOTE_AI_COST_SPIKE` | WARNING | Pico anômalo de custo do provedor |
