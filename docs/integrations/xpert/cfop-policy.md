# Política de CFOP — Sprint 6

Substitui a regra provisória `CFOP > '3000'` no filtro SQL por classificação explícita na aplicação, **separando natureza fiscal da elegibilidade para KPIs de combustível**.

## Duas dimensões

| Dimensão | Significado |
|----------|-------------|
| Natureza fiscal (`operation_class`, `fiscal_category`) | O que a operação é perante o CFOP |
| Escopo analítico (`default_analytics_scope`) | Se o item é candidato a volume/margem de combustível |

A entrada nos KPIs de combustível exige **todas** as condições:

1. CFOP com `operation_class = SALE` e escopo `FUEL_CANDIDATE`
2. Produto canônico do grupo combustível (`fuel_family` válido + unidade em litros)
3. Conversão de volume válida
4. Venda não cancelada

## Tratamentos persistidos

| Código | Significado |
|--------|-------------|
| `INCLUDE_AS_SALE` | Venda candidata a combustível (CFOP específico) |
| `INCLUDE_AS_SALE_GENERAL` | Venda geral de mercadoria — **não** entra automaticamente nos KPIs de combustível |
| `INCLUDE_AS_SALE_GENERAL_ST` | Venda geral com ST — idem |
| `INCLUDE_AS_RETURN` | Devolução — fato preservado, fora do consolidado |
| `EXCLUDE_NON_COMMERCIAL` | Operação não comercial |
| `PENDING_REVIEW` | Aguarda classificação — `PENDING_CFOP_CLASSIFICATION` |

## Homologação (filial 2443)

| CFOP | operation_class | fiscal_category | analytics_scope | review_status |
|------|-----------------|-----------------|-----------------|---------------|
| 5.656 | SALE | FUEL_OR_LUBRICANT | FUEL_CANDIDATE | CONFIRMED |
| 5.667 | SALE | FUEL_OR_LUBRICANT | FUEL_CANDIDATE | CONFIRMED (DBA 2026-07-10) |
| 5.102 | SALE | GENERAL_MERCHANDISE | NON_FUEL_BY_DEFAULT | PROVISIONAL_FISCAL_CONFIRMATION |
| 5.405 | SALE | GENERAL_MERCHANDISE_ST | NON_FUEL_BY_DEFAULT | PROVISIONAL_FISCAL_CONFIRMATION |
| Demais | UNKNOWN | UNCLASSIFIED | PENDING | PENDING_REVIEW |

### Exemplos

| Situação | Armazena fato | Receita geral | Volume combustível | Dashboard combustível |
|----------|---------------|---------------|--------------------|------------------------|
| Gasolina com 5.656 | Sim | Sim | Sim | Sim |
| Diesel com 5.667 | Sim | Sim | Sim | Sim |
| Aditivo / ARLA com 5.102 | Sim | Sim | Não | Não (`EXCLUDED_NON_FUEL_PRODUCT`) |
| Produto desconhecido com 5.102 | Sim | Sim | Não | Qualidade (`UNMAPPED_PRODUCT`) |
| CFOP desconhecido | Sim | — | Não | `PENDING_CFOP_CLASSIFICATION` |

## Conversão de unidade

| `source_unit` | Volume |
|---------------|--------|
| L / LT / litro | `quantity` |
| ML | `quantity / 1000` |
| UN / PC / CX | `UNIT_CONVERSION_REQUIRED` (sem fator cadastrado) |
| `null` + CFOP `FUEL_CANDIDATE` | assume litros (bomba) |
| `null` + CFOP geral | `UNIT_CONVERSION_REQUIRED` |

Embalagens (ex.: 1 UN = 0,200 L) só podem converter com fator explícito e **não** devem misturar volume de loja ao volume de bomba.

Configuração: `backend/app/core/cfop_policy.py`
