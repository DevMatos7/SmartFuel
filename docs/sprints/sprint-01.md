# Sprint 1 — Organizações, postos, usuários, autenticação e permissões

## Resultado

Sprint estrutural que entrega autenticação JWT, refresh com rotação, CRUD administrativo e autorização por perfil/posto.

## Bootstrap do primeiro administrador

```bash
docker compose exec backend python -m app.cli create-admin
```

## Variáveis principais

Ver `.env.example` — seção Autenticação.

## Documentação relacionada

- [Autenticação](../security/authentication.md)
- [Autorização](../security/authorization.md)
- [Sessões](../security/session-management.md)
- [Modelo de dados](../database/organizations-and-users.md)
- [Acesso por posto](../business-rules/station-access.md)
