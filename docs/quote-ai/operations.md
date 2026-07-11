# Operações — Quote AI

## Pré-requisitos

1. Migration `0024_sprint13_ai_quote_ingest` aplicada
2. Flag `quote_ai_ingestion_enabled=true` na organização (piloto: `POST /quote-ingestion/flags/enable-pilot`)
3. Cadastros mestres (distribuidora, produtos, posto, condição de pagamento)

## Rotas UI

| Rota | Função |
|------|--------|
| `/quotes/ai` | Importar texto / listar documentos |
| `/quotes/ai/batches` | Batches |
| `/quotes/ai/documents/:id` | Revisão |
| `/quotes/ai/quality` | Avaliação / resumo |
| `/quotes/ai/settings` | Provider |

## Checklist operacional

- [ ] Flags de e-mail/WhatsApp permanecem **false** até canal oficial
- [ ] Provider em produção: `mock` até homologação OpenAI
- [ ] Confirmar que create-draft não ativa cotação
- [ ] Monitorar alertas `QUOTE_AI_*`
- [ ] Limites de arquivo/batch (`QUOTE_AI_MAX_*` no `.env`)

## Limites de config

`QUOTE_AI_MAX_FILE_SIZE_MB` · `QUOTE_AI_MAX_BATCH_FILES` · `QUOTE_AI_MAX_BATCH_SIZE_MB` · `QUOTE_AI_MAX_PDF_PAGES` · `QUOTE_AI_MAX_IMAGE_PIXELS`

## Serviço central

`QuoteIngestionPipelineService` — único ponto operacional do pipeline.
