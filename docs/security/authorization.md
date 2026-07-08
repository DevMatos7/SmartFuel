# Autorização

## Perfis fixos

`ADMIN`, `GESTOR`, `COMPRADOR`, `FINANCEIRO`, `CONSULTA`

Permissões efetivas = união dos perfis do usuário.

## Permissões

Centralizadas em `app/core/permissions.py`:

- `organizations.read` / `organizations.write`
- `stations.read` / `stations.write`
- `users.read` / `users.write` / `users.manage_roles` / `users.manage_stations` / `users.reset_password`
- `audit.read`
- `dashboard.read`

## Regras

- Validação sempre no backend.
- `has_all_stations_access` apenas para ADMIN.
- Último ADMIN ativo protegido contra inativação/remoção de perfil.
