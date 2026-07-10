# Inteligência Auto Postos

Sistema interno de inteligência de compra, precificação e análise de combustíveis para o grupo de auto postos (XPERT ATX / SQL Server → PostgreSQL + FastAPI + React).

## Sprint atual

**Sprint 3.1 — Estabilização da Central de Cotações** concluída.

Sprint 3 (cotações) e sprints anteriores também disponíveis.

## Pré-requisitos

- Docker Desktop 4.x+ com Docker Compose v2
- Git
- (Opcional) Python 3.12 e Node 22 LTS para desenvolvimento local fora do Docker

## Configuração rápida

```bash
cp .env.example .env
# Ajuste senhas ilustrativas (POSTGRES_PASSWORD, MINIO_*) se desejar
docker compose up -d --build
```

Tempo estimado em máquina nova: **&lt; 30 minutos** (inclui download de imagens).

## URLs locais

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health (liveness) | http://localhost:8000/health |
| Health (readiness) | http://localhost:8000/api/v1/health |
| MinIO Console | http://localhost:9001 |

## Comandos Docker

```bash
# Iniciar
docker compose up -d --build

# Parar (mantém volumes)
docker compose down

# Rebuild forçado
docker compose up -d --build --force-recreate

# Logs (todos ou por serviço)
docker compose logs -f
docker compose logs -f backend

# Validar compose
docker compose config

# Limpar volumes de desenvolvimento (APAGA DADOS)
docker compose down -v
```

### Porta ocupada

Altere no `.env`: `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT`, `REDIS_PORT`, `MINIO_API_PORT`, `MINIO_CONSOLE_PORT`.

## Testes

```bash
# Subir banco de testes isolado
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d postgres_test

# Backend (obrigatório TEST_DATABASE_URL — ver docs/testing/test-database.md)
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm backend pytest -q

# Frontend
cd frontend && npm install && npm run test:run && npm run build
```

## Migrations (Alembic)

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1   # quando aplicável
```

## Desenvolvimento local

### Backend

Requer **Python 3.12** (não use 3.14 — wheels podem falhar).

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server: http://localhost:5173

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2
- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query
- Infra: Docker Compose, PostgreSQL 16, Redis 7, MinIO

## Documentação

- Arquitetura: [`docs/architecture/overview.md`](docs/architecture/overview.md)
- Decisões técnicas: [`docs/architecture/technical-decisions.md`](docs/architecture/technical-decisions.md)
- Sprint 0 (PDR/RDC): [`docs/sprints/sprint-00.md`](docs/sprints/sprint-00.md)
- Sprint 3 (cotações): [`docs/sprints/sprint-03.md`](docs/sprints/sprint-03.md)
- Sprint 3.1 (estabilização): [`docs/sprints/sprint-03-1-stabilization.md`](docs/sprints/sprint-03-1-stabilization.md)
- Regras de cotação: [`docs/business-rules/quotes.md`](docs/business-rules/quotes.md)
- Padrão de sprints: [`docs/sprints/README.md`](docs/sprints/README.md)
- BRIEF XPERT: [`docs/erp/xpert/CHECKLIST.md`](docs/erp/xpert/CHECKLIST.md)
- Roadmap: [`docs/sprints/roadmap.md`](docs/sprints/roadmap.md)

## Segurança

- Nunca versionar `.env` ou credenciais do XPERT
- Integração SQL Server apenas com usuário **somente leitura** (Sprint 5+)
- Logs e health checks não expõem connection strings

## Próxima sprint

**Sprint 4** — elegibilidade, custo equivalente e ranking de distribuidoras.
