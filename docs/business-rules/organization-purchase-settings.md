# Políticas de compra por organização

## Modelo

Tabela `organization_business_settings` — uma configuração por organização.

| Campo | Padrão | Descrição |
|-------|--------|-----------|
| `default_supplier_allowed` | `false` | Fornecedor sem regra explícita |
| `default_minimum_volume_liters` | `5000.000` | Volume mínimo padrão por produto |

## Resolução da regra efetiva

Ordem:

1. Regra específica (posto + distribuidora + produto [+ base])
2. Regra geral (posto + distribuidora [+ base])
3. **Configuração da organização** (`ORGANIZATION_DEFAULT`)
4. Ausência de regra (`NO_RULE` — não permitido)

## API

- `GET /api/v1/organization-business-settings`
- `PATCH /api/v1/organization-business-settings`

Permissões: leitura `organizations.read` (ADMIN, GESTOR); alteração `organizations.write` (ADMIN).

## Bootstrap

Variáveis `DEFAULT_SUPPLIER_ALLOWED` e `DEFAULT_MINIMUM_VOLUME_LITERS` são usadas **somente** na criação inicial da configuração. A fonte principal em runtime é o registro persistido.

## Auditoria

Alterações geram registro em `audit_logs` com `entity_type=organization_business_settings`.

## Base de distribuição (opcional)

Quando informada na consulta da regra efetiva, regras com `distribution_base_id` específico prevalecem sobre regras com base nula (qualquer base da distribuidora).
