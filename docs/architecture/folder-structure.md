# Estrutura de pastas

```text
inteligencia-auto-postos/   # workspace: Smart Fuel
├── backend/
│   ├── app/
│   │   ├── api/                # rotas HTTP
│   │   │   └── v1/
│   │   ├── core/               # config, logging, exceptions
│   │   ├── models/             # SQLAlchemy (sprints futuras)
│   │   ├── schemas/            # Pydantic
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── integrations/
│   │   │   └── xpert/          # conector SQL Server (Sprint 5+)
│   │   ├── workers/
│   │   └── main.py
│   ├── migrations/             # Alembic
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       ├── modules/
│       ├── pages/
│       ├── services/
│       └── hooks/
├── infra/
│   └── nginx/
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── erp/xpert/queries/
│   └── sprints/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Convenções

- Código de domínio em `services/`; controllers apenas orquestram.
- Consultas XPERT versionadas em `docs/erp/xpert/queries/` e carregadas pelo conector.
- Uma sprint = migrations + testes + docs atualizados + Compose funcional.
