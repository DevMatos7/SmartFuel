# Ciclo de vida da cotação

## Transições permitidas (RDC-009)

```
DRAFT ──► ACTIVE
DRAFT ──► CANCELLED

ACTIVE ──► EXPIRED
ACTIVE ──► CANCELLED
ACTIVE ──► SUPERSEDED

EXPIRED, CANCELLED, SUPERSEDED → estados finais (sem retorno a ACTIVE)
```

## Rascunho (RDC-010)

Em `DRAFT`:

- Cabeçalho, itens e evidências podem ser alterados
- Não entra em análises de mercado futuras
- Histórico funcional e auditoria são registrados

## Ativação (RDC-011)

Validações obrigatórias:

1. Posto ativo e autorizado
2. Distribuidora ativa
3. `quoted_at` e `valid_until` futura
4. Ao menos um item válido (preço > 0, produto ativo, condição válida)
5. Evidência conforme canal (RDC-012)
6. `expected_version` correspondente
7. Permissão `quotes.activate`

Após ativação: `activated_at`, `activated_by`, bloqueio comercial, histórico e auditoria.

## Cancelamento (RDC-039)

- Exige motivo e permissão `quotes.cancel`
- Idempotente
- Cotação permanece consultável

## Revisão (RDC-014)

1. `POST /api/v1/quotes/{id}/revise` com motivo
2. Cria nova cotação `DRAFT` com `replaces_quote_id`
3. Copia cabeçalho e itens
4. Original permanece `ACTIVE` até ativação da revisão
5. Ao ativar revisão: original → `SUPERSEDED`, `superseded_by_quote_id` preenchido

## Duplicação (RDC-015)

- Cria `DRAFT` para outro posto e/ou novas datas
- Copia itens
- Evidências **não** são copiadas por padrão (`copy_evidences: false`)

## Expiração (RDC-016, RDC-017)

- Job: `POST /api/v1/quotes/expiration/run` (permissão `quote_expiration.execute`)
- Marca `ACTIVE` → `EXPIRED` quando `valid_until <= agora`
- Idempotente; não altera canceladas ou substituídas
- Itens com validade específica podem expirar antes do cabeçalho

## Histórico funcional (RDC-037)

Separado da auditoria geral (`audit_log`). Ações: `CREATED`, `HEADER_UPDATED`, `ITEM_*`, `EVIDENCE_*`, `ACTIVATED`, `EXPIRED`, `CANCELLED`, `REVISION_CREATED`, `SUPERSEDED`, `DUPLICATED`, `SUPPLEMENTAL_EVIDENCE_ADDED`.

Consulta: `GET /api/v1/quotes/{id}/history`
