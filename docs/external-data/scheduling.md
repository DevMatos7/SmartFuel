# Agendamento de fontes externas

Independente do scheduler XPERT.

`scheduler_enabled` só pode ser `true` quando:

1. status/conector `HOMOLOGATED`
2. `secret_ref` presente se exigir credenciais
3. termos `APPROVED`
4. `metadata.contract_validated = true`
5. `metadata.rate_limit` configurado
6. `metadata.manual_homologation_done = true`

Caso contrário: API retorna 400 e agenda permanece OFF.

CSOnline / AuthorizedWeb: sempre `MISCONFIGURED` até mecanismo autorizado confirmado.
