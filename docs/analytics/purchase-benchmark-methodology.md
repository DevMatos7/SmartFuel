# Metodologia — Compra real × melhor cotação

## Princípio

Comparação **histórica sem viés retrospectivo**:

Compra em T → somente cotações conhecidas em T → regras e parâmetros vigentes em T → melhor opção elegível em T.

## Unidade

`nota + posto + produto canônico` (itens do mesmo produto na mesma nota são agrupados).

## Custo

Modo padrão `DELIVERED_COST`:

- Real: `Σ commercial_delivered_cost / Σ volume_liters`
- Benchmark: custo entregue da melhor cotação elegível (motor Sprint 4)

## Diferenças

- `cost_variance_per_liter = actual − benchmark`
- `opportunity_amount = max(variance_total, 0)`
- `actual_advantage_amount = max(−variance_total, 0)`

Não rotular automaticamente como “prejuízo”.

## Motor

Reutiliza `QuoteEvaluationService`, `CandidateEvaluationContext`, ranking e `snapshot_canonical`. Não duplica fórmulas da Sprint 4.

## Fonte

Benchmark opera só no PostgreSQL. XPERT permanece UNSAFE / agenda bloqueada / produção com `sa` bloqueada.
