# Acesso seguro a evidências

## Princípios (RDC-035, RNF-008)

1. Bucket MinIO **privado** — sem acesso público direto
2. Download apenas via backend, com autenticação e escopo por posto
3. Usuário só acessa evidências de cotações dos postos autorizados
4. URLs assinadas temporárias quando aplicável (`SIGNED_URL_EXPIRE_SECONDS`, padrão 300 s)

## Fluxo

```
Cliente autenticado
    → GET /api/v1/quotes/{id}/evidences/{evidence_id}
    → Backend valida permissão quote_evidences.read + escopo do posto
    → ObjectStorage gera stream ou URL pré-assinada
    → Arquivo entregue sem expor credenciais MinIO
```

## Permissões

| Ação | Permissão |
|------|-----------|
| Visualizar / download | `quote_evidences.read` |
| Upload | `quote_evidences.write` |
| Inativar em cotação ativa | `quote_evidences.deactivate` (ADMIN) |

## Logs (RNF-009)

Erros de upload **não** expõem: caminho interno, credenciais MinIO, stack trace ao cliente.

## Inativação administrativa

- Arquivo permanece no storage para auditoria
- Metadados: `deactivated_by`, `deactivated_at`, `deactivation_reason`
- `active = false` — não conta para validação de ativação nem listagens operacionais
