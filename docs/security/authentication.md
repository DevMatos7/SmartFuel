# Autenticação

## Estratégia

- **Access token (JWT)**: 15 minutos (configurável), mantido em memória no frontend.
- **Refresh token**: 7 dias, hash SHA-256 no PostgreSQL, cookie HttpOnly (`refresh_token`).
- **Rotação**: cada refresh invalida o token anterior e emite um novo na mesma família.
- **Reutilização**: refresh revogado com motivo `rotated` reutilizado revoga a família.

## Endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

## Senha

- Hash **bcrypt** via Passlib.
- Política mínima: 8 caracteres, letra, número, diferente do e-mail.

## Rate limit

Login limitado por IP + identificador via Redis (`LOGIN_RATE_LIMIT` / `LOGIN_RATE_WINDOW_SECONDS`).

Em produção, configure `LOGIN_RATE_ALLOW_MEMORY_FALLBACK=false` para não liberar tentativas ilimitadas se o Redis estiver indisponível.

## Troca obrigatória de senha

Dependency `get_current_active_user` bloqueia rotas administrativas quando `must_change_password=true`.

Rotas permitidas com senha pendente:

- `GET /auth/me`
- `POST /auth/change-password`
- `POST /auth/logout`
- `POST /auth/refresh`
