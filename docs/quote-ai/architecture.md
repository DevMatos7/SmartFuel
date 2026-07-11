# Arquitetura — Ingestão de cotações por IA

## Papel da IA

Extrair e sugerir. Não ativar cotação, não escrever no XPERT, não criar cadastro mestre.

## Fluxo

```
documento/texto
  → validação de segurança
  → batch + document (sha256)
  → MockQuoteExtractionProvider (ou provedor configurado)
  → quote_ai_extractions + quote_extraction_fields
  → quote_ingestion_entity_matches
  → quote_ingestion_reviews (PENDING → revisão humana)
  → approve → READY_FOR_DRAFT
  → create-draft → Quote (origin=AI_ASSISTED_INGESTION, status DRAFT)
  → ativação manual na Central de Cotações
```

## Componentes

| Componente | Função |
|------------|--------|
| `QuoteIngestionPipelineService` | Orquestra ingestão, extração, matching, review e rascunho |
| `MockQuoteExtractionProvider` | Extração determinística para homologação |
| `QuoteDocumentSecurityService` | Extensão, MIME, assinatura, tamanho |
| Frontend `/quotes/ai` | Importação, filas, revisão e qualidade |

## Persistência (migration `0024`)

Batches → documents → extractions/fields → entity matches → reviews → draft links · provider configs · evaluation cases/runs.

## Multi-tenant

Todas as queries filtram `organization_id`. Documento duplicado: unique `(organization_id, sha256)`.
