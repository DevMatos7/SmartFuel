# Sprint 1.1 — Estabilização da identidade, autorização e auditoria

## Objetivo

Fechar lacunas da Sprint 1 sem antecipar funcionalidades da Sprint 2.

## Entregas

- Dependency `get_current_active_user` para bloqueio de `MUST_CHANGE_PASSWORD`
- Testes backend ampliados (sessão, autorização, domínio, auditoria, rate limit)
- Formulário de usuário com vínculo completo de postos
- Tela de auditoria com filtros, paginação e detalhes
- Vitest + React Testing Library para fluxos críticos do frontend
- Rate limit: fallback em memória apenas fora de produção

## Comandos

```bash
docker compose run --rm backend pytest -q
cd frontend && npm run test:run && npm run build
```

## CSRF

Refresh e logout usam cookie HttpOnly com `SameSite=Lax`. Endpoints exigem credenciais cross-origin bloqueadas pelo navegador em cenários típicos. Documentado em `docs/security/session-management.md`.

## Pendências remanescentes

- Argon2id (dívida técnica)
- MFA e recuperação por e-mail (Sprint futura)
- Gestão avançada de sessões por dispositivo
