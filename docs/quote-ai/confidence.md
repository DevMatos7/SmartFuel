# Confiança

## Níveis

| Escopo | Onde |
|--------|------|
| Documento | `quote_ai_extractions.document_confidence` |
| Campo | `quote_extraction_fields.confidence` |
| Matching | `quote_ingestion_entity_matches.match_confidence` |

## Mock (homologação)

- Item típico: ~0.94
- Documento: média entre confiança de preço e 0.85
- Sem itens: ~0.20 + warning `NO_ITEMS_EXTRACTED`

## Uso operacional

- Confiança &lt; 0.70 → alerta `QUOTE_AI_LOW_CONFIDENCE`
- Baixa confiança **não** bloqueia revisão; reforça atenção humana
- Confiança **nunca** autoriza ativação automática
