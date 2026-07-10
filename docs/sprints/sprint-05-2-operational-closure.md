# Sprint 5.2 — Fechamento operacional XPERT

## Objetivo

Concluir lacunas operacionais que impedem o encerramento formal da Sprint 5, sem antecipar a Sprint 6.

## Entregas

### Backend
- Testes de concorrência com duas sessões PostgreSQL reais (`test_xpert_sprint52_concurrency.py`)
- Claim `FOR UPDATE SKIP LOCKED` comprovado
- Advisory lock e `SKIPPED_LOCKED` comprovados
- Unicidade de checkpoint global (`NULLS NOT DISTINCT`)
- Atomicidade: COMPLETED avança; PARTIAL/FAILED preservam checkpoint
- Recuperação `FAILED_WORKER_LOST` e retry
- Agenda com `FOR UPDATE SKIP LOCKED` em datasets

### Frontend
- Página de checkpoints com reset (motivo obrigatório)
- Fonte: criar/editar/testar conexão
- Datasets: contrato, agenda, overlap, batch, habilitação
- Execuções: detalhe com staging, erros agrupados, cancel/retry
- Testes Vitest ampliados

### Documentação
- Runbook em `operations.md` e `checkpoints.md`
- Este documento

## Gate externo (Sprint 5 formal)

Homologação real SQL Server continua obrigatória:
- incremental com overlap
- preservação de mapeamento em re-sync
- cancelamento/retry controlado em ambiente real

## Comandos

```bash
# Testes backend XPERT
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest tests/test_xpert_sprint52_concurrency.py -q

# Smoke conexão (quando SQL Server acessível)
docker compose run --rm backend python scripts/smoke_xpert_connection.py

# Homologação API
docker compose exec backend python scripts/homolog_xpert_api.py
```
