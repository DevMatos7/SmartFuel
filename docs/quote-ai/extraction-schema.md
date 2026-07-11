# Schema de extração (v1)

Saída estruturada gravada em `quote_ai_extractions.structured_output`.

## Campos principais

```json
{
  "document_type": "QUOTE_MESSAGE",
  "distributor": { "raw_name": "...", "cnpj": null, "confidence": 0.9, "evidence": "..." },
  "base": { "raw_name": "...", "confidence": 0.88 },
  "quote_datetime": null,
  "valid_until": { "raw": "...", "hour": 16, "origin": "EXTRACTED" },
  "valid_until_origin": "EXTRACTED",
  "items": [
    {
      "raw_product_name": "Diesel S10",
      "price_per_liter": "6.2100",
      "currency": "BRL",
      "minimum_volume_liters": "5000",
      "payment_terms": [{ "raw_text": "7 dias", "days": 7, "price_per_liter": "6.2100" }],
      "freight": { "type": null, "amount": null },
      "confidence": 0.94,
      "evidence": "..."
    }
  ],
  "warnings": [],
  "unparsed_fragments": []
}
```

## Regras

- Não inventar campos ausentes
- Preço ≤ 0 ou inválido → warning de validação determinística
- Campos espelhados em `quote_extraction_fields` (`field_path`, `value_origin`, `confidence`, `evidence_text`)
- `schema_version` / `prompt_version` versionados na extração
