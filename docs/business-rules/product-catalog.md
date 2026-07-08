# Catálogo de produtos canônicos

## Conceito

Produto canônico é o cadastro padronizado usado em indicadores e regras. Famílias iniciais: `ETHANOL`, `GASOLINE_C`, `DIESEL_B_S10`, `DIESEL_B_S500`. Variantes: `COMMON`, `ADDITIVATED`.

## Regras

- Código único e imutável após uso (`code_locked` quando mapeado por produto ERP)
- Exclusão lógica (`active=false`)
- Unidade inicial: `LITER`
- Produto inativo não aparece em novos mapeamentos

## Endpoints

- `GET/POST /api/v1/products`
- `PATCH /api/v1/products/{id}`
- `POST /api/v1/products/{id}/deactivate|reactivate`

## Permissões

- Leitura: todos os perfis autenticados com `products.read`
- Escrita/inativação: apenas `ADMIN`
