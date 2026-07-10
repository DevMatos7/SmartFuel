# Snapshots de comparação

## Conteúdo persistido

- Cenário informado
- Parâmetro financeiro vigente na data
- Regra comercial resolvida por candidato
- Componentes de custo e memória de cálculo
- Motivos de elegibilidade
- Ranking e indicadores
- Versão da metodologia (`QUOTE_COMPARISON_V1`)

## Imutabilidade

Execuções `COMPLETED` não são recalculadas. Reprocessamento cria nova execução com `reprocessed_from_run_id`.

## Hash canônico

SHA-256 sobre JSON canônico com:

- Chaves ordenadas
- Datas em ISO UTC
- Decimais como strings
- Listas em ordem determinística
- Sem `processing_duration_ms` ou `request_id`

Implementação: `app/domain/quote_comparison/snapshot_canonical.py`

## Contexto imutável

`CandidateEvaluationContext` resolve regra, custos e elegibilidade uma única vez por candidato.
