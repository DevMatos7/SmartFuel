# Central de Cotações

## Visão geral

A Central de Cotações registra propostas comerciais recebidas das distribuidoras (WhatsApp, portal, telefone, e-mail) de forma estruturada, auditável e vinculada a um posto.

Cada cotação pertence a **um único posto** (RDC-001). Para reutilizar condições em outro posto, use **duplicação**.

## Cabeçalho

| Campo | Obrigatório na ativação | Observação |
|-------|-------------------------|------------|
| Posto | Sim | Deve estar ativo e autorizado ao usuário |
| Distribuidora | Sim | Pode gerar alerta se sem regra explícita (RDC-003) |
| Base | Não | Deve pertencer à distribuidora quando informada |
| Data da cotação | Sim | `quoted_at` |
| Validade | Sim | Futura em relação à ativação; `valid_until > quoted_at` |
| Canal | Sim | WHATSAPP, PORTAL, EMAIL, PHONE, OTHER |
| Método | Padrão MANUAL | IMPORT e API reservados |
| Vendedor / contato | PHONE | Obrigatórios para canal telefone |
| Descrição da origem | OTHER | Obrigatória |
| Observações | Não | Texto livre |

## Numeração

`quote_number` é sequencial por organização (`organization_id + quote_number` único).

## Status persistido

`DRAFT`, `ACTIVE`, `EXPIRED`, `CANCELLED`, `SUPERSEDED`

## Status efetivo

Calculado em runtime (RDC-017): cotações `ACTIVE` com `valid_until <= agora` são tratadas como expiradas antes do job de expiração persistir `EXPIRED`.

## Imutabilidade

Cotações `ACTIVE` não permitem alteração de campos comerciais, itens ou remoção de evidências originais. Correções exigem **revisão** (RDC-013, RDC-014).

## Concorrência

Campo `version` com `expected_version` nos comandos de escrita. Conflito retorna `409 QUOTE_VERSION_CONFLICT` (RDC-036).

## Endpoints principais

- `GET/POST /api/v1/quotes`
- `GET/PATCH /api/v1/quotes/{id}`
- `POST /api/v1/quotes/{id}/activate`
- `POST /api/v1/quotes/{id}/cancel`
- `POST /api/v1/quotes/{id}/revise`
- `POST /api/v1/quotes/{id}/duplicate`
- `GET /api/v1/quotes/{id}/history`
- `GET /api/v1/quotes/{id}/export/pdf`

Ver também: [quote-lifecycle.md](./quote-lifecycle.md), [quote-items.md](./quote-items.md).
