# Staging XPERT

## Tabela `erp_staging_records`

Cada linha extraída passa pelo staging antes do domínio (`erp_products`, `erp_suppliers`).

## Campos principais

- `raw_payload`: JSON bruto da origem
- `normalized_payload`: após normalização (CNPJ, datas, strings)
- `source_key`: chave natural obrigatória
- `content_hash`: hash canônico para idempotência
- `status`: por fase (`STAGED`, `QUARANTINED`, `APPLIED`, etc.)

## Hash canônico

Ordem das chaves no JSON não altera o hash. CNPJ formatado e sem formatação convergem. Datas equivalentes em UTC geram o mesmo hash.

## Quarentena

Payload inválido ou fora do contrato vai para quarentena. Run pode terminar `PARTIAL`; checkpoint não avança se `allow_partial_checkpoint=false` (padrão).

## Duplicidade na mesma run

Mesma `source_key` duplicada na execução gera erro registrado em `erp_sync_errors`.

## Preservação de mapeamentos

Aplicação atualiza campos de origem mas **não** substitui:

- `canonical_product_id` / vínculo distribuidor
- `mapping_status`, `ignore_reason`, `mapped_by`, `mapped_at`
