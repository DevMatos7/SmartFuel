# Sprint 0 — Fundação técnica e arquitetura

## Objetivo

Criar monorepo, Docker Compose, FastAPI, frontend React e documentação base — sem regras de negócio.

## Escopo entregue

- Backend FastAPI com `/health` e `/api/v1/health`
- Frontend Vite + React + Tailwind com página técnica de status
- PostgreSQL, Redis, MinIO no Compose
- Alembic preparado (sem tabelas de negócio)
- Ruff + Pytest
- Docs de arquitetura e pasta de queries XPERT
- Variáveis preparadas para SQL Server (sem conexão ativa)

## Critérios de aceite

- [x] `docker compose up -d` sobe backend, frontend, postgres, redis, minio
- [x] `GET /health`, `GET /api/v1/health`, `GET /docs`
- [x] Frontend exibe status da API
- [x] Sem autenticação / cotações / tabelas de negócio

## Fora de escopo

Auth, products, quotes, sync XPERT, nginx obrigatório.
