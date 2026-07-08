# Sprint 2.1 — Estabilização dos cadastros mestres

**Status:** Concluída  
**Dependência:** Sprint 2  
**Migration:** `0004_sprint21_org_settings`

## Objetivo

Fechar lacunas de qualidade e configuração sem antecipar Sprint 3 (cotações).

## Entregas

### Isolamento de testes

- `TEST_DATABASE_URL` obrigatória com guardas em `tests/db_guard.py`
- `docker-compose.test.yml` com serviço `postgres_test` (tmpfs, porta 5433)
- Fixtures com Alembic + rollback por teste (sem `create_all` no banco dev)

### Configuração por organização

- Tabela `organization_business_settings`
- API GET/PATCH `/api/v1/organization-business-settings`
- `SupplierRuleService` usa configuração persistida
- UI "Políticas de compra" em Organização

### Bootstrap

- `MasterDataBootstrapService` — produtos, condições e settings idempotentes
- CLI `seed-master-data` atualizado

### Frontend

- `ErpSupplierImportPage` — importação CSV de fornecedores
- 25 testes Vitest adicionados (fluxos Sprint 2)

## Comandos

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest -q
cd frontend && npm run test:run && npm run build
docker compose exec backend alembic upgrade head
```

## Fora do escopo (confirmado)

Cotações, SQL Server, ranking, compras/vendas, estoque.
