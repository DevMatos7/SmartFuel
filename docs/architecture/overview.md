# Arquitetura — Inteligência Auto Postos

## Visão geral

O sistema consome o ERP **XPERT ATX** (SQL Server 2022) em **somente leitura**, sincroniza dados para um banco operacional próprio (**PostgreSQL**) e oferece módulos de cotações, compras, vendas, mercado e BI.

```text
ERP XPERT ATX / SQL Server (1..N instâncias)
          ↓ leitura (pyodbc, usuário read-only)
Serviço de integração e sincronização
          ↓
PostgreSQL (operacional + analítico)
          ↓
Cotações + Compras + Vendas + Mercado + BI
```

O sistema **não escreve** no banco do XPERT (sem INSERT/UPDATE/DELETE/DDL).

## Stack

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Banco da aplicação | PostgreSQL |
| Cache / filas | Redis + Dramatiq/Celery (a partir das sprints de sync) |
| Evidências | MinIO |
| ERP | SQL Server 2022 via pyodbc |
| Deploy | Docker Compose → servidor próprio → futura VPS Linux |

## Separação de bancos

- **SQL Server** = fonte de verdade operacional do XPERT (por posto/instância).
- **PostgreSQL** = histórico, regras de negócio, cotações, BI e auditoria da aplicação.

## Multi-instância XPERT

Há pelo menos quatro conexões distintas (matriz e filiais). A integração trata cada origem como um conector configurável vinculado a `station_id`.

## Fronteiras de responsabilidade

1. **Integração**: extrai e versiona consultas SQL; grava staging + tabelas canônicas.
2. **Domínio**: cotações, elegibilidade, custo equivalente, decisões de compra.
3. **Analytics**: consolidações diárias, dashboards, índices de mercado.
4. **Evidências**: arquivos em MinIO com hash SHA-256 e trilha de auditoria.

## Segurança

- Credenciais apenas via variáveis de ambiente.
- Usuário SQL do XPERT com privilégio de leitura.
- Sem segredos no código ou no Git.
- Auditoria de alterações relevantes (Sprint 1+).

## Deploy

Ambiente local/on-premise com Docker. Quando migrar para VPS, preferir **agente de sincronização local** (Opção B) para não expor o SQL Server na internet.
