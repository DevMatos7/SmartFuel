# Sprint 0 — Fundação técnica e arquitetura

> **PDR** = Documento de Requisitos do Produto  
> **RDC** = Regras de Domínio e Critérios

---

## 1. Identificação da sprint

| Item | Definição |
|------|-----------|
| Projeto | Inteligência Auto Postos |
| Sprint | Sprint 0 |
| Nome | Fundação técnica e arquitetura |
| Tipo | Estrutural |
| Duração sugerida | 5 dias úteis |
| Prioridade | Crítica |
| Dependência | Nenhuma |
| Resultado esperado | Ambiente completo executando via Docker |
| Repositório | [DevMatos7/SmartFuel](https://github.com/DevMatos7/SmartFuel) |

---

## 2. PDR — Documento de Requisitos do Produto

### 2.1 Contexto

O projeto será uma plataforma interna para inteligência de compras, preços, vendas, margens e indicadores do mercado de combustíveis.

A aplicação deverá integrar futuramente:

- ERP XPERT ATX
- SQL Server 2022
- PostgreSQL próprio
- Cotações recebidas por WhatsApp
- Portais de distribuidoras
- XML de NF-e
- Brent, dólar, CEPEA, ANP
- Dados de vendas, estoque, compras e preços

Antes de desenvolver funcionalidades comerciais, é necessário criar uma fundação técnica segura, modular e preparada para crescer.

### 2.2 Problema

Sem uma estrutura inicial padronizada, o projeto corre riscos de:

- Dependência direta do ERP
- Código desorganizado
- Mistura entre regras de negócio e integração
- Dificuldade para executar em diferentes servidores
- Falta de controle das variáveis de ambiente
- Dificuldade para testar
- Acúmulo de decisões técnicas inconsistentes
- Migração complicada para VPS futuramente

### 2.3 Objetivo da sprint

Criar a estrutura-base da aplicação, contendo:

- Backend FastAPI
- Frontend React
- PostgreSQL
- Redis
- MinIO
- Docker Compose
- Alembic
- Testes automatizados
- Health checks
- Logs
- Documentação
- Estrutura preparada para integração com o XPERT

### 2.4 Objetivos de negócio

Mesmo sem funcionalidades comerciais nesta sprint, ela deverá permitir:

- Reduzir risco técnico nas próximas etapas
- Padronizar o desenvolvimento
- Facilitar implantação em servidor próprio
- Preparar migração futura para VPS Linux
- Garantir que novos módulos sejam construídos de forma desacoplada
- Permitir diagnóstico rápido de indisponibilidade

### 2.5 Métricas de sucesso

| Métrica | Meta |
|---------|------|
| Serviços iniciados pelo Docker Compose | 100% |
| Testes do backend aprovados | 100% |
| Build do frontend aprovado | 100% |
| Endpoints de saúde funcionando | 100% |
| Segredos versionados no Git | 0 |
| Serviços com health check | No mínimo backend, PostgreSQL, Redis e MinIO |
| Tempo de configuração em nova máquina | Inferior a 30 minutos |
| Erros críticos de inicialização | 0 |

### 2.6 Premissas

- O servidor inicial poderá utilizar Windows ou Linux com Docker
- O banco SQL Server do XPERT permanecerá externo ao Docker
- O sistema terá banco PostgreSQL próprio
- O acesso ao ERP será somente leitura
- A integração com o ERP não será implementada nesta sprint
- A autenticação não será implementada nesta sprint
- O projeto será inicialmente interno
- A arquitetura deverá funcionar posteriormente em uma VPS Linux

---

## 3. Escopo

### 3.1 Dentro do escopo

**Backend**

- Projeto FastAPI
- Configurações por ambiente
- SQLAlchemy 2
- Conexão com PostgreSQL
- Alembic
- Endpoints de saúde
- Tratamento global de exceções
- Logs estruturados
- Configuração de CORS
- Estrutura modular

**Frontend**

- React, TypeScript, Vite, Tailwind CSS, TanStack Query
- Página técnica inicial
- Consulta ao health check do backend
- Estados de carregamento e indisponibilidade

**Infraestrutura**

- Docker Compose, PostgreSQL, Redis, MinIO
- Volumes persistentes, redes internas, health checks
- Arquivo `.env.example`

**Qualidade**

- Pytest, Ruff, build do frontend, documentação inicial

### 3.2 Fora do escopo

Não será implementado nesta sprint:

- Login, usuários, permissões, postos
- Produtos, distribuidoras, cotações
- Integração SQL Server / ERP XPERT
- Importação de vendas ou compras
- Dashboard comercial, web scraping, indicadores externos
- Upload funcional de documentos
- Regras de margem e cálculos regulatórios

---

## 4. Personas e permissões

| Persona | Responsabilidade nesta sprint | Permissões |
|---------|------------------------------|------------|
| **Desenvolvedor** | Executar projeto, testes, migrations, diagnóstico | Acesso total ao código e ambiente local |
| **Administrador de infraestrutura** | Subir containers, variáveis, monitorar saúde | Docker, `.env`, logs |
| **Usuário de negócio** | Visualizar página técnica inicial | Somente leitura pública da tela inicial (sem auth) |

Nesta sprint não há controle de acesso — qualquer pessoa com URL local acessa a página técnica.

---

## 5. RDC — Regras de domínio e critérios

| ID | Regra |
|----|-------|
| **RDC-001** | PostgreSQL é o banco principal; SQL Server é fonte externa futura |
| **RDC-002** | Tabelas XPERT só via `app/integrations/xpert/` |
| **RDC-003** | Credenciais e segredos apenas por variáveis de ambiente |
| **RDC-004** | Indisponibilidade do XPERT não impede startup do backend |
| **RDC-005** | `GET /health` responde sem consultar banco ou outros serviços |
| **RDC-006** | `GET /api/v1/health` verifica backend, PostgreSQL, Redis e MinIO |
| **RDC-007** | Estados: `healthy`, `degraded`, `unhealthy` |
| **RDC-008** | PostgreSQL e MinIO com volumes persistentes; Redis sem persistência obrigatória nesta etapa |
| **RDC-009** | Logs em stdout; sem senhas, tokens ou connection strings completas |
| **RDC-010** | Mudanças no PostgreSQL somente via Alembic |
| **RDC-011** | Datas armazenadas em UTC |
| **RDC-012** | Decisões estruturais em `docs/` |

---

## 6. Requisitos funcionais

| ID | Requisito |
|----|-----------|
| **RF-001** | Aplicação FastAPI executável |
| **RF-002** | Aplicação React executável |
| **RF-003** | `GET /health` com status `ok` |
| **RF-004** | `GET /api/v1/health` com verificação de dependências |
| **RF-005** | Página técnica com status, versão e última verificação |
| **RF-006** | `.env.example` sem valores sensíveis reais |
| **RF-007** | Alembic configurado e conectável ao PostgreSQL |
| **RF-008** | `/docs`, `/redoc`, `/openapi.json` funcionais |

---

## 7. Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| **RNF-001** | Portabilidade via Docker Compose |
| **RNF-002** | Nenhum segredo no repositório |
| **RNF-003** | Separação `api` / `core` / `models` / `schemas` / `services` / `integrations` |
| **RNF-004** | `/health` &lt; 500 ms sem dependência de banco |
| **RNF-005** | Logs com data, nível, serviço, mensagem; request ID quando disponível |
| **RNF-006** | Testes automatizados nos health checks |
| **RNF-007** | Python 3.12; Node LTS compatível com Vite |
| **RNF-008** | Página responsiva (desktop, tablet, celular) |
| **RNF-009** | Contraste, textos legíveis, estados não só por cor, foco visível |

---

## 8. Casos de uso

### UC-001 — Inicializar o ambiente

**Ator:** Desenvolvedor ou administrador  
**Pré-condições:** Docker e Compose instalados; `.env` configurado  
**Fluxo:** `cp .env.example .env` → `docker compose up -d --build` → serviços sobem → health checks OK → usuário acessa app  
**Resultado:** Todos os serviços saudáveis  

**Alternativas:** PostgreSQL indisponível (degraded); porta ocupada (erro Docker + README)

### UC-002 — Consultar saúde básica

**Fluxo:** `GET /health` → HTTP 200 → processo ativo

### UC-003 — Consultar saúde completa

**Fluxo:** `GET /api/v1/health` → testes de PG/Redis/MinIO → status consolidado

### UC-004 — Visualizar status no frontend

**Fluxo:** Acessar página → loading → consulta API → exibe status e horário  
**Alternativa:** API offline → mensagem amigável + botão “Verificar novamente”

### UC-005 — Executar migrations

**Fluxo:** `alembic upgrade head` com PostgreSQL disponível

### UC-006 — Executar testes

**Fluxo:** `pytest` no backend; `npm run build` no frontend

---

## 9. Fluxos de UX

### 9.1 Objetivo

Tela técnica que confirma instalação correta — não é dashboard comercial.

### 9.2 Wireframe

```text
┌────────────────────────────────────────────────────┐
│ Inteligência Auto Postos                           │
│ Plataforma de inteligência de combustíveis        │
├────────────────────────────────────────────────────┤
│ Status geral          [● Sistema operacional]    │
│ API                   Operacional                  │
│ Banco de dados        Operacional                  │
│ Redis                 Operacional                  │
│ Arquivos              Operacional                  │
│ Última verificação: 08/07/2026 15:32               │
│ [ Verificar novamente ]                            │
├────────────────────────────────────────────────────┤
│ Versão frontend | Versão API                       │
└────────────────────────────────────────────────────┘
```

### 9.3 Estados visuais

| Estado | Comportamento |
|--------|---------------|
| Carregando | Skeleton/spinner — “Verificando os serviços” |
| Saudável | “Todos os serviços estão operacionais” |
| Degradado | “Sistema disponível, mas há instabilidade” |
| Indisponível | “Não foi possível conectar ao servidor” |

### 9.4 Regras de UX

- Sem stack trace, credenciais ou endereço interno de banco
- Nova tentativa sem reload completo da página
- Texto + cor + ícone; horário da última tentativa; responsivo

---

## 10. Arquitetura e decisões técnicas

### 10.1 Diagrama

```text
Navegador → Frontend React → Backend FastAPI
                                  ├─ PostgreSQL
                                  ├─ Redis
                                  ├─ MinIO
                                  └─ (futuro) XPERT → SQL Server 2022
```

### 10.2 Estrutura do projeto

Ver [folder-structure.md](../architecture/folder-structure.md) e [technical-decisions.md](../architecture/technical-decisions.md).

### 10.3 Serviços Docker

| Serviço | Porta host (padrão) |
|---------|---------------------|
| Backend | 8000 |
| Frontend | 3000 (Nginx; dev local 5173) |
| PostgreSQL | 5432 |
| Redis | 6379 |
| MinIO API / Console | 9000 / 9001 |

---

## 11. Variáveis de ambiente

Ver `.env.example` na raiz. Mínimo exigido pelo PDR:

`APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_VERSION`, `BACKEND_*`, `POSTGRES_*`, `REDIS_*`, `MINIO_*`, `CORS_ORIGINS`, `XPERT_SQLSERVER_*`

Valores ilustrativos apenas — nunca credenciais reais do XPERT.

---

## 12. Modelo de dados

Nesta sprint **não há tabelas de negócio**.

- Migration baseline: `0001_sprint0_baseline` (vazia)
- Não criar: usuários, empresas, postos, produtos, cotações, auditoria de negócio

---

## 13. Contratos de API

### `GET /health`

**200 — Liveness**

```json
{
  "status": "ok",
  "service": "inteligencia-auto-postos-api",
  "version": "0.1.0",
  "timestamp": "2026-07-08T19:30:00Z"
}
```

### `GET /api/v1/health`

**200 — Saudável (contrato alvo)**

```json
{
  "status": "healthy",
  "timestamp": "2026-07-08T19:30:00Z",
  "version": "0.1.0",
  "services": {
    "api": { "status": "healthy", "response_time_ms": 1 },
    "database": { "status": "healthy", "response_time_ms": 12 },
    "redis": { "status": "healthy", "response_time_ms": 4 },
    "object_storage": { "status": "healthy", "response_time_ms": 15 }
  }
}
```

**200 — Degradado**

```json
{
  "status": "degraded",
  "services": {
    "api": { "status": "healthy" },
    "database": { "status": "healthy" },
    "redis": { "status": "unhealthy", "message": "Service unavailable" },
    "object_storage": { "status": "healthy" }
  }
}
```

Mensagens não expõem host, credencial ou connection string.

### Erros (formato alvo)

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Ocorreu um erro inesperado.",
    "request_id": "8c88244b-6e2e-4e98-8bfe-7fe13bcd32cc"
  }
}
```

---

## 14. Tratamento de erros

- Formato padronizado com `code`, `message`, `request_id` (alvo)
- Em desenvolvimento, detalhes nos logs — não necessariamente na resposta HTTP

---

## 15. Critérios de aceite

| ID | Critério | Status |
|----|----------|--------|
| CA-001 | `docker compose up -d --build` inicia todos os serviços | ✅ |
| CA-002 | `/health` retorna HTTP 200 | ✅ |
| CA-003 | `/api/v1/health` verifica PG, Redis, MinIO | ⚠️ MinIO só `configured` |
| CA-004 | Frontend mostra estado da API | ✅ |
| CA-005 | Mensagem amigável se API indisponível | ✅ |
| CA-006 | Botão “Verificar novamente” | ⚠️ Auto-refresh 15s; botão pendente |
| CA-007 | `.env.example` presente | ✅ |
| CA-008 | Nenhuma senha real versionada | ✅ |
| CA-009 | Alembic funcional | ✅ |
| CA-010 | Pytest aprovado | ✅ |
| CA-011 | Ruff sem erros bloqueantes | ✅ |
| CA-012 | Build frontend aprovado | ✅ |
| CA-013 | README com comandos completos | ⚠️ Parcial |
| CA-014 | Preparado para SQL Server sem conectar | ✅ |

---

## 16. Plano de testes

### Backend

| # | Cenário | Status |
|---|---------|--------|
| T1 | Health básico HTTP 200 | ✅ |
| T2 | Health detalhado saudável | ✅ |
| T3 | Banco indisponível | ✅ |
| T4 | Redis indisponível | ✅ |
| T5 | Request ID | ✅ |
| T6 | Ocultação de credenciais | ✅ |

### Frontend

| # | Cenário | Status |
|---|---------|--------|
| T7 | Renderização | ✅ manual |
| T8 | Estados loading / saudável / degradado / indisponível | ✅ |
| T9 | Nova tentativa (botão) | ✅ |
| T10 | Build TypeScript | ✅ |

### Infraestrutura

| # | Cenário | Status |
|---|---------|--------|
| T11 | Compose sobe ambiente vazio | ✅ |
| T12 | Volumes PostgreSQL / MinIO | ✅ |
| T13 | `alembic upgrade head` | ✅ |

---

## 17. Definition of Ready

- [x] Stack aprovada
- [x] Docker disponível
- [x] Nome do projeto definido
- [x] Portas parametrizadas
- [x] Estrutura-base acordada
- [x] Repositório GitHub criado

---

## 18. Definition of Done

- [x] Critérios de aceite principais atendidos
- [x] Backend, frontend e Compose validados
- [x] PostgreSQL, Redis, MinIO conectados/configurados
- [x] Alembic, testes e build OK
- [x] Documentação inicial
- [x] Sem segredos versionados
- [x] Sprint 1 não antecipada
- [x] Critérios de aceite CA-001 a CA-014 atendidos

---

## 19. Entregáveis

| Entregável | Caminho |
|------------|---------|
| Compose | `docker-compose.yml` |
| Env exemplo | `.env.example` |
| Git ignore | `.gitignore` |
| README | `README.md` |
| Backend | `backend/` |
| Frontend | `frontend/` |
| Infra | `infra/` |
| Docs arquitetura | `docs/architecture/` |
| Docs sprint | `docs/sprints/sprint-00.md` |
| Queries XPERT | `docs/erp/xpert/queries/*.sql` |

---

## 20. Tarefas técnicas sugeridas

Lista de referência — ver seção 22 para o que já foi concluído e o que permanece como débito.

---

## 21. Riscos e dependências

| Risco | Impacto | Tratamento |
|-------|---------|------------|
| Porta ocupada | Médio | Portas configuráveis no `.env` |
| Driver SQL Server ausente | Baixo (Sprint 0) | Só preparar variáveis |
| Containers no Windows | Médio | Docker Desktop; paths neutros |
| Dependências incompatíveis | Médio | Versões fixadas; Python 3.12 no container |
| MinIO indisponível | Baixo | Health degraded |
| Segredos no Git | Alto | `.gitignore` + revisão |
| Backend depende do banco para iniciar | Médio | Startup separado de readiness |
| Complexidade excessiva | Médio | Não antecipar módulos |

**Dependências:** Nenhuma sprint anterior.

---

## 22. Status de implementação (pós-entrega)

**Sprint 0 implementada conforme PDR/RDC.**

### Entregue

- Contrato `/health` com `inteligencia-auto-postos-api`
- Contrato `/api/v1/health` com `services`, `response_time_ms`, estados `healthy`/`degraded`/`unhealthy`
- Ping real PostgreSQL, Redis e MinIO
- Middleware `X-Request-ID` e erros `{ error: { code, message, request_id } }`
- Frontend com estados loading/saudável/degradado/indisponível e botão **Verificar novamente**
- Testes automatizados de health, falhas simuladas, request ID e erros
- `precos_venda.sql` (alias de `preco_venda.sql`)
- Documentação e README completos

### Observações

- Redis sem volume persistente — conforme RDC-008
- Frontend Docker na porta `3000`; Vite dev na `5173`
- `app/core/database.py` concentra acesso ao PostgreSQL (equivalente ao `db/` do diagrama)

### Débito técnico residual

- Testes de UI automatizados (Vitest) — apenas build TS nesta sprint
- Padronização de erros 422 de validação FastAPI — se necessário na Sprint 1

---

## 23. Script completo para o Cursor IA

```text
PROJETO: INTELIGÊNCIA AUTO POSTOS
SPRINT: 0
NOME: FUNDAÇÃO TÉCNICA E ARQUITETURA

Atue como arquiteto de software e desenvolvedor full stack sênior.

Antes de implementar qualquer alteração:

1. Inspecione integralmente o repositório.
2. Identifique estruturas, arquivos e configurações já existentes.
3. Preserve tudo que estiver funcional e compatível com a arquitetura.
4. Não recrie arquivos apenas por preferência estética.
5. Não implemente funcionalidades previstas para sprints futuras.
6. Registre decisões técnicas relevantes na documentação.

==================================================
1. CONTEXTO DO PROJETO
==================================================

Plataforma interna para cotações, integração XPERT ATX, análise de compras/vendas/margens,
índices de mercado e evidências gerenciais.

Operação inicial: 1 matriz + 3 filiais (4 postos), 2 bandeira branca + 2 Shell.
Nenhuma regra comercial nesta sprint.

==================================================
2. OBJETIVO DA SPRINT
==================================================

Fundação: FastAPI + React + PostgreSQL + Redis + MinIO + Docker + Alembic + testes + docs.

==================================================
3. REGRAS OBRIGATÓRIAS
==================================================

- Sem SQLite, auth, usuários, postos, produtos, cotações, sync XPERT real.
- Sem credenciais reais; sem escrita no SQL Server.
- UTC; Alembic para schema; código tipado.
- Logs sem segredos.

==================================================
4–16. IMPLEMENTAÇÃO
==================================================

Seguir docs/sprints/sprint-00.md seções 3–21.
Contratos de API: seção 13.
Critérios de aceite: seção 15.

==================================================
17. RELATÓRIO FINAL OBRIGATÓRIO
==================================================

Ao concluir, forneça: resumo funcional/técnico, arquivos criados/alterados, serviços Docker,
variáveis, migrations, testes, resultados, comandos, URLs, pendências, riscos, decisões,
confirmação de que Sprint 1 não foi antecipada.

Não avance para a Sprint 1.
```

---

## Próxima sprint

**Sprint 1 — Organizações, postos, usuários, autenticação e permissões**  
Documento: `docs/sprints/sprint-01.md` (a criar com [TEMPLATE.md](./TEMPLATE.md)).
