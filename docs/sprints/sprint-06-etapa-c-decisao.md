# Decisão formal — Etapa C (Sprint 6) e liberação Sprint 7

Data: 2026-07-10

## Etapa C — 30 dias

**APROVADA OPERACIONALMENTE**

Evidências principais:

- Produto histórico 1136 localizado (ATIVO=0 omitido por filtro antigo)
- Produtos inativos sincronizados com `source_active`
- Defesa de referência órfã (migration 0014)
- Reexecuções COMPLETED, zero duplicidades
- Volume elegível 160.739,87 L / receita líquida R$ 976.244 / agregações 30/30
- Fato 1971639:2150248 preservado fora dos KPIs (UNMAPPED_PRODUCT + EXCLUDED_NON_FUEL_PRODUCT)

## Status Sprint 6

| Item | Status |
|------|--------|
| Etapa A | APROVADA |
| Etapa B | APROVADA |
| Etapa C | APROVADA OPERACIONALMENTE |
| Carga histórica / idempotência / agregações / isolamento | HOMOLOGADOS |
| Incremental contínuo | PENDENTE |
| Confirmação `source_updated_at` | PENDENTE |
| Formas de pagamento | PENDENTE |
| Agenda automática | BLOQUEADA (fonte UNSAFE) |

## Decisão Sprint 7

**LIBERADA** para desenvolvimento e homologação controlada, mantendo usuário `sa`.

| Controle | Valor |
|----------|-------|
| Fonte XPERT | UNSAFE — sa |
| Ambiente | development/homologação |
| Execução | manual ADMIN |
| Agenda | bloqueada |
| Produção | bloqueada enquanto usar sa |
| Sprint 8 | NÃO AUTORIZADA |

Confirmação textual de homologação de compras: `CONFIRMAR HOMOLOGAÇÃO DE COMPRAS XPERT`
