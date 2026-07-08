# Banco de testes PostgreSQL

Os testes de integração **nunca** devem usar `DATABASE_URL` da aplicação.

## Configuração

```env
TEST_DATABASE_URL=postgresql+asyncpg://smartfuel_test:smartfuel_test@localhost:5433/smartfuel_test
TEST_DATABASE_URL_SYNC=postgresql+psycopg://smartfuel_test:smartfuel_test@localhost:5433/smartfuel_test
```

## Proteções

- `TEST_DATABASE_URL` obrigatória — pytest falha se ausente
- Bloqueio quando `TEST_DATABASE_URL == DATABASE_URL`
- Nome do banco deve conter `_test` (ou `TEST_DATABASE_ALLOW_UNSAFE=true`)

## Docker

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest -q
```

## Estratégia de fixtures

1. **Session:** `alembic upgrade head` no banco de testes (uma vez)
2. **Teste:** transação externa com rollback — commits da API usam savepoints
3. **Factories:** flush sem commit; dados isolados por teste

Não utilizar `Base.metadata.create_all()` / `drop_all()` no banco de desenvolvimento.

## Migrations

Suíte dedicada em `tests/test_migrations.py` recria schema em banco vazio e valida tabelas + seeds idempotentes.
