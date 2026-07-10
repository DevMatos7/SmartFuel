# Scheduler de expiração de cotações

## Serviço Docker

O Compose inclui o serviço `quote_scheduler`, que executa:

```bash
python -m app.workers.quote_scheduler
```

Intervalo configurável via `QUOTE_EXPIRATION_INTERVAL_MINUTES` (padrão: 15 minutos).

## Comportamento

1. Chama `QuoteExpirationService.run(origin="SCHEDULER")` diretamente — **não** usa HTTP.
2. Processa cotações `ACTIVE` em lotes (`QUOTE_EXPIRATION_BATCH_SIZE`, padrão 500).
3. Usa `compute_effective_status` para decidir expiração integral.
4. Persiste `EXPIRED`, registra histórico e auditoria.
5. Idempotente: reexecução não altera cotações já finalizadas.

## Lock de concorrência

Advisory lock PostgreSQL (`pg_try_advisory_lock`) com chave fixa `738291047`.

Se outra instância já estiver executando:

- Retorna `{"skipped": true, "reason": "lock_not_acquired"}`.
- Não gera erro.

## Endpoint manual (mantido)

`POST /api/v1/quotes/expiration/run` — permissão `quote_expiration.execute` (ADMIN).

Útil para execução sob demanda em desenvolvimento ou recuperação.

## Comandos

```bash
# Subir scheduler com a stack
docker compose up -d quote_scheduler

# Logs
docker compose logs -f quote_scheduler

# Execução manual via API
curl -X POST http://localhost:8000/api/v1/quotes/expiration/run \
  -H "Authorization: Bearer <token_admin>"
```

## Variáveis

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `QUOTE_EXPIRATION_INTERVAL_MINUTES` | 15 | Intervalo do scheduler |
| `QUOTE_EXPIRATION_BATCH_SIZE` | 500 | Máximo por execução |
| `QUOTE_EXPIRATION_LOCK_TIMEOUT_SECONDS` | 300 | Referência para timeout do lock |
