# Configuração de provedor

Tabela `quote_ai_provider_configs` (por organização).

## Defaults

| Campo | Default |
|-------|---------|
| `provider` | `mock` |
| `model` | `mock-extractor-v1` |
| `prompt_version` / `schema_version` | `v1` |
| `temperature` | `0` |
| `allow_training_usage` | false |
| `enabled` | false (seed operacional; factory local pode criar mock habilitado para piloto) |

Limites opcionais: `daily_cost_limit`, `monthly_cost_limit`, `per_document_cost_limit`.

## Seleção em runtime

`get_quote_extraction_provider()`:

- `mock` → `MockQuoteExtractionProvider`
- `openai` → `OpenAIQuoteExtractionProvider` (**stub**; exige `secret_ref` homologado)

Se o config da org não estiver `enabled`, o pipeline força `mock`.

## API

- `GET/PUT /quote-ingestion/provider-config` (`quote_ingestion.manage_provider`)
- Flag `quote_ai_provider_enabled` (default false) para uso de provedor externo em produção

Secrets: apenas `secret_ref` (referência), nunca chave em plaintext no banco/logs.
