# Regras de fornecimento por posto

## Precedência

1. Regra específica (posto + distribuidora + produto)
2. Regra geral (posto + distribuidora, `product_id` nulo)
3. Política padrão da organização (`DEFAULT_SUPPLIER_ALLOWED`, `DEFAULT_MINIMUM_VOLUME_LITERS`)
4. Ausência de regra

## Volume mínimo

Padrão: 5.000 litros por produto. Volumes de produtos diferentes não são somados.

## Vigência

Regra válida quando `valid_from <= data` e (`valid_until` nulo ou `data <= valid_until`).

Sobreposições para mesma combinação são bloqueadas.

## Regra efetiva

`GET /api/v1/station-supplier-rules/effective?station_id=&distributor_id=&product_id=&reference_date=`

Retorna `allowed`, `minimum_volume_liters`, `rule_source`, `rule_id`, vigência.

## Endpoints CRUD

- `GET/POST /api/v1/station-supplier-rules`
- `PATCH /api/v1/station-supplier-rules/{id}`
- `POST .../close-validity|deactivate|reactivate`
