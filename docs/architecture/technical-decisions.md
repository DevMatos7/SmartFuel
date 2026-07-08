# Decisões técnicas

Registro das decisões estruturais relevantes. Atualizar a cada sprint quando houver mudança de direção.

## ADR-001 — Banco operacional separado do ERP

**Status:** Aceito (Sprint 0)

PostgreSQL é o banco da aplicação. SQL Server (XPERT ATX) é fonte externa somente leitura, acessada via `app/integrations/xpert/`.

**Motivo:** não sobrecarregar o ERP, preservar histórico e permitir regras próprias de cotação/BI.

---

## ADR-002 — Docker Compose como ambiente padrão

**Status:** Aceito (Sprint 0)

Desenvolvimento e implantação inicial usam Docker Compose com backend, frontend, PostgreSQL, Redis e MinIO.

**Motivo:** reprodutibilidade, migração futura para VPS Linux e tempo de setup &lt; 30 min.

---

## ADR-003 — Backend assíncrono com SQLAlchemy 2

**Status:** Aceito (Sprint 0)

FastAPI + SQLAlchemy 2 async (`asyncpg`) para o PostgreSQL. Alembic com driver síncrono (`psycopg`) para migrations.

---

## ADR-004 — Evidências em MinIO

**Status:** Aceito (Sprint 0, uso a partir da Sprint 3)

Arquivos (XML, PDF, prints) não ficam no PostgreSQL; armazenamento em MinIO com hash SHA-256.

---

## ADR-005 — Health check em dois níveis

**Status:** Aceito (Sprint 0)

- `GET /health` — liveness (processo vivo, sem dependências).
- `GET /api/v1/health` — readiness agregado (PostgreSQL, Redis, MinIO).

**Evolução planejada:** contrato com objeto `services`, tempos de resposta e estados `healthy` / `degraded` / `unhealthy` (ver sprint-00, seção 13).

---

## ADR-006 — Python 3.12 no container

**Status:** Aceito (Sprint 0)

Imagem Docker `python:3.12-slim`. Desenvolvimento local no Windows deve usar 3.12 (não 3.14) por compatibilidade de wheels (`pydantic-core`, `asyncpg`).

---

## ADR-007 — Frontend servido por Nginx em produção Docker

**Status:** Aceito (Sprint 0)

Build Vite → Nginx na porta 80 do container (mapeada para `3000` no host). Dev local continua em `5173`.

---

## ADR-008 — Multi-instância XPERT

**Status:** Identificado (pré-Sprint 5)

Há múltiplos servidores SQL Server por filial. O conector tratará uma configuração por `station_id`.

---

## ADR-009 — Datas em UTC no backend

**Status:** Aceito (Sprint 0)

Armazenamento e APIs em UTC; conversão para fuso do posto nas camadas de apresentação (Sprint 1+).
