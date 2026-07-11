# Segurança do parser XML NF-e

- Biblioteca: `defusedxml` (bloqueio XXE / entidades externas)
- Limite de tamanho: 5 MiB
- Sem requests remotos durante o parse
- SHA-256 do arquivo original
- Chave de acesso: exatamente 44 dígitos; inválida não é “corrigida”
- Falhas registradas em `parse_errors` / `parse_status=PARSE_ERROR`
