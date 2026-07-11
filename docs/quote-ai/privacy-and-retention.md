# Privacidade e retenção

## Dados sensíveis

Documentos podem conter preços comerciais, nomes de distribuidoras e metadados de remetente (`source_sender`, `source_message_datetime`).

## Controles

- `view_raw_text` / `view_ai_payload` / `download_document` — permissões explícitas
- `allow_training_usage=false` — não autorizar uso para treino do provedor
- Isolamento por `organization_id`
- Hash SHA-256 para deduplicação sem reprocessar cópias idênticas

## Retenção

Alinhar a `docs/operations/data-retention.md`:

- Extractions e reviews: retenção operacional definida pela org
- Não enviar payload bruto a provedores externos sem autorização e flag
- Arquivamento futuro via status `ARCHIVED` (permissão `quote_ingestion.archive`)

Não gravar API keys; apenas `secret_ref`.
