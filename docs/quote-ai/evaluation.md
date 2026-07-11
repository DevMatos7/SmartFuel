# Avaliação de qualidade

## Objetivo

Medir regressão do extrator (principalmente `MockQuoteExtractionProvider`) antes de evoluir prompt/schema.

## Tabelas

- `quote_extraction_evaluation_cases` — casos com `expected_output`
- `quote_extraction_evaluation_runs` — execução, pass/fail, métricas

## API

`POST /quote-ingestion/evaluations/runs` (`quote_ingestion.run_evaluation`)

1. Seed de casos sintéticos (texto simples, prompt injection, multi-produtos)
2. Roda `MockQuoteExtractionProvider`
3. Compara quantidade de itens e primeiro preço

Flag: `quote_ai_evaluation_enabled` (default false — uso operacional sob controle).

UI: `/quotes/ai/quality` + analytics summary.
