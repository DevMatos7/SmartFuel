# Segurança — Integração XPERT

## Princípios

1. **Somente leitura** no SQL Server — validação estática (sqlglot) + conta dedicada.
2. **Credenciais externas** via `secret_ref` (Docker Secret / arquivo / env de desenvolvimento).
3. **Queries versionadas** no repositório — sem editor SQL na interface.
4. **Defesa em profundidade** — mesmo com GRANT indevido, apenas SELECT passa no validador.

## Privilégios verificados

- Papéis: `sysadmin`, `db_owner`, `db_datawriter`
- Permissões efetivas: `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `CONTROL`, `EXECUTE`

Fonte `UNSAFE` bloqueia sincronização quando `XPERT_ALLOW_UNSAFE_PRIVILEGES=false`.

## Transporte

- `Encrypt=yes` preferencial
- `TrustServerCertificate` apenas com alerta administrativo

## Logs e auditoria

Nunca registrar: senha, connection string completa, payload integral em log comum.
