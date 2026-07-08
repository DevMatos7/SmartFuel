# Gestão de sessões

## Modelo `auth_sessions`

- `refresh_token_hash` (nunca o token puro)
- `token_family_id` para detectar reutilização
- `revoked_at` / `revoked_reason`

## Revogação

- Logout da sessão atual
- Inativação de usuário
- Alteração/redefinição de senha
- Organização inativa (bloqueio no refresh)

## Cookies

| Variável | Padrão |
|----------|--------|
| `REFRESH_COOKIE_NAME` | `refresh_token` |
| `REFRESH_COOKIE_SECURE` | `false` (dev) |
| `REFRESH_COOKIE_SAMESITE` | `lax` |

Path do cookie: `/api/v1/auth`

## CSRF

O refresh token via cookie utiliza `SameSite=Lax` por padrão, reduzindo envio em requisições cross-site. Em produção, combine com `Secure=true` e origens CORS restritas. Logout e refresh exigem cookie + sessão válida no servidor.
