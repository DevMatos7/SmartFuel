# Sprint 13 — Ingestão inteligente de cotações por IA

**Status:** Fundação + homologação sintética liberadas.

**Proibições:** escrita XPERT · ativação automática de cotação · criação automática de cadastro mestre · WhatsApp não oficial · Sprint 14.

## Princípios

| Princípio | Regra |
|-----------|--------|
| IA extrai apenas | Sugere campos estruturados; não decide negócio |
| Humano revisa | Todo documento passa por `NEEDS_REVIEW` |
| Sem autoativação | Rascunho `DRAFT` apenas; ativação na Central de Cotações |
| Sem master data auto | Distribuidora/produto/posto devem existir e ser confirmados |
| Sem escrita XPERT | Pipeline só lê cadastros locais e grava no PG Smart Fuel |
| Sem WhatsApp não oficial | Canais `WHATSAPP_*` existem no enum; flag off por padrão |

## Entregue

- Migration `0024_sprint13_ai_quote_ingest`
- Models: batches, documents, extractions, fields, entity matches, reviews, draft links, provider configs, evaluation cases/runs
- `MockQuoteExtractionProvider` (parser determinístico) + stub `OpenAIQuoteExtractionProvider`
- `QuoteIngestionPipelineService` — upload/texto → extração → matching → revisão → rascunho
- APIs `/api/v1/quote-ingestion/*` e `/api/v1/analytics/quote-ingestion/*`
- Frontend `/quotes/ai` (import, batches, review, quality, settings)
- Origem de cotação `AI_ASSISTED_INGESTION`
- Feature flags (default **false** para ingestão, e-mail e WhatsApp)
- Testes `tests/test_quote_ingestion_sprint13.py`
- Docs em `docs/quote-ai/`

## Feature flags (default seguro)

| Flag | Default |
|------|---------|
| `quote_ai_ingestion_enabled` | false |
| `quote_ai_email_channel_enabled` | false |
| `quote_ai_whatsapp_channel_enabled` | false |
| `quote_ai_image_upload_enabled` | false |
| `quote_ai_pdf_upload_enabled` | false |
| `quote_ai_spreadsheet_enabled` | false |
| `quote_ai_provider_enabled` | false |
| `quote_ai_evaluation_enabled` | false |

Piloto: `POST /quote-ingestion/flags/enable-pilot` (ADMIN) liga apenas `quote_ai_ingestion_enabled` na org.

## APIs (resumo)

- `POST /quote-ingestion/text` · `POST /quote-ingestion/batches` · upload de documentos
- Listagem de batches/documents · detalhe com campos, matches e review
- Review: start / save / approve / reject
- `POST .../create-draft` → quote com `origin=AI_ASSISTED_INGESTION`, **nunca** ativada
- Provider config · evaluation runs · analytics summary

## Homologação

| Etapa | Conteúdo | Status |
|-------|----------|--------|
| A | Testes sintéticos + `MockQuoteExtractionProvider` | Liberada |
| B | Colagem de texto + revisão humana + rejeição | Liberada (sintético) |
| C | Matching de entidades + criação de rascunho (sem ativar) | Liberada (sintético) |
| D | Harness de avaliação (`/evaluations/runs`) | Liberada (casos sintéticos) |
| E | Provedor real / e-mail / WhatsApp oficial | **Bloqueada** (flags off + OpenAI stub) |

## Confirmações

- XPERT somente leitura (inalterado)
- Ativação automática: **proibida**
- Sprint 14: **não iniciada / não antecipada**
