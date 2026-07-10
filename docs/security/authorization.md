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
- `quotes.read` / `quotes.write` / `quotes.activate` / `quotes.cancel` / `quotes.revise` / `quotes.duplicate`
- `quote_items.write`
- `quote_evidences.read` / `quote_evidences.write` / `quote_evidences.deactivate`
- `quote_history.read`
- `quote_expiration.execute`

Cadastros mestres (Sprint 2): `products.*`, `erp_products.*`, `distributors.*`, etc.

## Matriz resumida — cotações (Sprint 3)

| Recurso | ADMIN | GESTOR | COMPRADOR | FINANCEIRO | CONSULTA |
|---------|-------|--------|-----------|------------|----------|
| Visualizar | Sim | Sim | Sim | Sim | Sim |
| Criar/editar rascunho | Sim | Sim | Sim | Não | Não |
| Ativar / cancelar / revisar | Sim | Sim | Sim | Não | Não |
| Duplicar | Sim | Não | Sim | Não | Não |
| Evidências (upload) | Sim | Sim | Sim | Não | Não |
| Inativar evidência (ativa) | Sim | Não | Não | Não | Não |
| Expiração manual | Sim | Não | Não | Não | Não |

## Regras

- Validação sempre no backend.
- `has_all_stations_access` apenas para ADMIN.
- Último ADMIN ativo protegido contra inativação/remoção de perfil.
