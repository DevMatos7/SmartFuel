# Inteligência Auto Postos

Sistema interno de inteligência de compra, precificação e análise de combustíveis para o grupo de auto postos (XPERT ATX / SQL Server → PostgreSQL + FastAPI + React).

## Sprint atual

**Sprint 0 — Fundação técnica** (sem autenticação, sem tabelas de negócio).

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2
- Frontend: React, TypeScript, Vite, Tailwind CSS, TanStack Query
- Infra: Docker Compose, PostgreSQL 16, Redis 7, MinIO

## Subir com Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Serviços:

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Health detalhado | http://localhost:8000/api/v1/health |
| MinIO console | http://localhost:9001 |

## Backend local (sem Docker da app)

Requer **Python 3.12** (não use 3.14 nesta etapa — wheels de `pydantic-core`/`asyncpg` podem falhar).

```bash
cd backend
py -3.12 -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Testes e lint (preferencialmente no container):

```bash
docker compose exec backend pytest -q
docker compose exec backend ruff check app tests
```

Ou localmente com o venv 3.12:

```bash
cd backend
pytest
ruff check app tests
```

Migrations:

```bash
cd backend
alembic upgrade head
```

## Frontend local

```bash
cd frontend
npm install
npm run dev
```

Build:

```bash
cd frontend
npm run build
```

## Documentação

- Arquitetura: [`docs/architecture/overview.md`](docs/architecture/overview.md)
- BRIEF + checklist XPERT: [`docs/erp/xpert/CHECKLIST.md`](docs/erp/xpert/CHECKLIST.md)
- Queries versionadas: [`docs/erp/xpert/queries/`](docs/erp/xpert/queries/)
- Sprint 0: [`docs/sprints/sprint-00.md`](docs/sprints/sprint-00.md)
- Roadmap: [`docs/sprints/roadmap.md`](docs/sprints/roadmap.md)

## Segurança

- Nunca versionar senhas do XPERT ou da aplicação.
- Integração SQL Server apenas com usuário **somente leitura**.
- Variáveis XPERT estão no `.env.example` sem valores reais.

## Próxima sprint

Após revisão desta fundação: **Sprint 1 — organizações, postos, usuários e JWT**.
