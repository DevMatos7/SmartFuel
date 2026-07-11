# Importação manual

Fluxo: upload → preview → validação → **confirmação** → aplicação.

Suporta CSV (XLSX estruturado para evolução). Decimal com vírgula ou ponto. Valor ausente **não** vira zero.

Endpoints:
- `POST /external-data/import/preview`
- `POST /external-data/import/confirm`
- `POST /external-data/series/{id}/observations` (valor individual)
