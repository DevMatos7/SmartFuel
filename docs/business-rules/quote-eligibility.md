# Elegibilidade de propostas

## Estados

| Estado | Descrição |
|--------|-----------|
| `ELIGIBLE` | Atende todas as regras obrigatórias |
| `ELIGIBLE_WITH_WARNINGS` | Pode ranquear, mas possui alertas |
| `INELIGIBLE` | Não ocupa ranking elegível |

## Regra de validade

`comparison_datetime < effective_valid_until`

No instante exato de `valid_until`, o item é considerado vencido.

## Resolução histórica

- Cotação conhecida: `activated_at <= comparison_datetime`
- Estado ativo na data: não cancelada, substituída ou vencida antes da comparação
- Regras comerciais: vigência em `comparison_datetime`, ignorando `active` administrativo
- Parâmetro financeiro: vigência em `comparison_datetime`

## Motivos bloqueantes

Ver `app/domain/quote_comparison/eligibility.py` — códigos `BLOCKING` impedem ranking.

## Motivos de alerta

Códigos `WARNING` permitem ranking com destaque visual.

## Contexto imutável

Cada candidato é avaliado uma única vez via `CandidateEvaluationContext`, garantindo consistência entre elegibilidade, custos e snapshot.
