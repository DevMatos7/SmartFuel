# Distribuidoras e bases

## Distribuidora

- CNPJ único por organização quando informado
- Sem CNPJ: status `INCOMPLETE`
- Nome normalizado para detecção de duplicidade

## Base de distribuição

- Pertence a uma distribuidora
- UF válida (sigla de 2 letras)
- Nome normalizado único por distribuidora + estado

## Fornecedor ERP

Chave: `station_id + erp_entity_id`. Mapeamento segue mesma lógica de status dos produtos ERP.

## Endpoints

- `/api/v1/distributors`
- `/api/v1/distribution-bases`
- `/api/v1/erp-suppliers`
