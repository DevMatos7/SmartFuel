# Sprint 2 — Cadastros mestres e mapeamento ERP

**Status:** Concluída  
**Dependência:** Sprint 1  
**Migration:** `0003_sprint2_master_data`

## Entregas

### Backend

- 9 tabelas de cadastros mestres + importação
- 8 services de domínio
- 8 routers API (`/api/v1/products`, `erp-products`, `distributors`, etc.)
- Seeds idempotentes (6 produtos + 6 condições de pagamento)
- 17 novos testes (`test_sprint2_master_data.py`)

### Frontend

- Menu **Cadastros** com 6 telas principais
- Mapeamento ERP com drawer e lote
- Importação CSV em etapas
- Simulador de regra efetiva

### Documentação

- `docs/database/master-data.md`
- `docs/business-rules/*` (produtos, mapeamento, distribuidoras, condições, regras)
- `docs/integrations/xpert-master-data-import.md`

## Permissões adicionadas

`products.*`, `erp_products.*`, `distributors.*`, `distribution_bases.*`, `payment_terms.*`, `supplier_rules.*`, `master_data_imports.*`

## Comandos

```bash
# Migration
docker compose exec backend alembic upgrade head

# Seed manual
docker compose exec backend python -m app.cli seed-master-data --organization-id <UUID>

# Testes
docker compose run --rm --no-deps backend pytest tests/ -q
cd frontend && npm run test:run && npm run build
```

## Fora do escopo (confirmado)

Conexão SQL Server, cotações, ranking, compras/vendas, estoque, NF-e, IA para mapeamento.

## Decisões técnicas

- Política padrão de fornecedor via variáveis de ambiente (`DEFAULT_SUPPLIER_ALLOWED=false`)
- Volume mínimo padrão: 5000 litros (`DEFAULT_MINIMUM_VOLUME_LITERS`)
- CNPJ de distribuidora: índice único parcial (apenas quando informado)
- `code_locked` em produtos quando utilizados em mapeamento ERP
