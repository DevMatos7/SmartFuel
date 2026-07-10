# Evidências de cotação

## Armazenamento

- Binários no **MinIO** (bucket `MINIO_QUOTE_EVIDENCE_BUCKET`, padrão `quote-evidences`)
- Metadados no PostgreSQL (`quote_evidences`)
- Fallback em memória nos testes quando MinIO indisponível

## Metadados (RDC-030)

| Campo | Descrição |
|-------|-----------|
| `original_file_name` | Nome enviado pelo usuário |
| `stored_file_name` | Nome interno aleatório |
| `content_type` / `file_extension` | Tipo MIME e extensão |
| `size_bytes` | Tamanho |
| `sha256` | Hash SHA-256 (RDC-033) |
| `storage_key` | Chave no bucket |
| `category` | SCREENSHOT, PORTAL_DOCUMENT, EMAIL, SPREADSHEET, PDF_PROPOSAL, OTHER |
| `is_supplemental` | Evidência adicional pós-ativação |
| `active` | Falso quando inativada administrativamente |

## Tipos permitidos (RDC-031)

PDF, PNG, JPG, JPEG, WEBP, XLSX, CSV. Executáveis bloqueados.

## Limites (RDC-032)

- Tamanho máximo: `QUOTE_EVIDENCE_MAX_SIZE_MB` (padrão 10 MB)
- Validação de extensão, MIME e assinatura básica

## Duplicidade (RDC-033)

Hash SHA-256 calculado no upload. Arquivo idêntico na mesma cotação → `DUPLICATE_EVIDENCE`.

## Obrigatoriedade (RDC-012)

| Canal | Requisito |
|-------|-----------|
| WHATSAPP, PORTAL, EMAIL | Ao menos uma evidência ativa |
| PHONE | Vendedor, contato e observação no cabeçalho |
| OTHER | `source_description` |

## Ciclo de vida (RDC-034)

- **Rascunho**: upload e remoção permitidos
- **Ativa**: evidências originais imutáveis; suplementares permitidas; inativação apenas ADMIN com motivo (`quote_evidences.deactivate`)

## Endpoints

- `POST /api/v1/quotes/{id}/evidences` (multipart)
- `GET /api/v1/quotes/{id}/evidences/{evidence_id}` (download/stream)
- `DELETE /api/v1/quotes/{id}/evidences/{evidence_id}` (rascunho)
- `POST /api/v1/quotes/{id}/evidences/{evidence_id}/deactivate` (ativa, ADMIN)

Ver: [evidence-access.md](../security/evidence-access.md)
