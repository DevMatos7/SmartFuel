# Restore runbook

1. Restaurar dump em ambiente isolado.
2. Validar `alembic current`.
3. Smoke: login, health, um dashboard.
4. Registrar `restore_drill_at` em `backup_verification_records`.
5. Não usar produção com fonte XPERT `sa`.
