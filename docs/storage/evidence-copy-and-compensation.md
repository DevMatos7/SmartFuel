# Cópia de evidências e compensação de storage

## Cópia na duplicação (`copy_evidences: true`)

Estratégia: **cópia física** no MinIO.

1. Lê objeto de origem (`storage_key` da evidência original).
2. Grava em nova chave: `quotes/{org_id}/{nova_cotação}/{uuid}{ext}`.
3. Cria novo registro em `quote_evidences` com:
   - Mesmo `sha256` (permitido entre cotações diferentes).
   - `source_evidence_id` apontando para a evidência de origem.
   - `uploaded_by` = usuário que duplicou.
   - `uploaded_at` = momento da cópia.

## Atomicidade

A duplicação (cotação + itens + evidências) ocorre em uma transação lógica:

- Falha na cópia de qualquer evidência → rollback da transação.
- Objetos já copiados no storage são removidos (compensação).

## Upload com compensação

Fluxo de upload (`QuoteEvidenceService.upload`):

1. Valida arquivo.
2. Calcula SHA-256.
3. Grava no MinIO.
4. Persiste metadados no PostgreSQL.
5. Se a persistência falhar → `delete_object` na chave criada.

## Fallback em memória

| Ambiente | `OBJECT_STORAGE_ALLOW_MEMORY_FALLBACK` |
|----------|--------------------------------------|
| Produção / scheduler | `false` |
| Testes (pytest) | `true` (via conftest) |

Com `false`, falha do MinIO interrompe o upload com `503 STORAGE_UNAVAILABLE` — **sem** gravar metadados órfãos.

## Objetos órfãos

Não há job de limpeza automática nesta sprint. A compensação ocorre na mesma requisição em caso de falha pós-upload.

Recomendação futura: job periódico listando chaves sem referência em `quote_evidences`.
