# Ranking de propostas

## Modos

| Modo | Custo utilizado |
|------|-----------------|
| `RAW` | Preço bruto por litro |
| `DELIVERED` | Custo entregue por litro |
| `FINANCIAL_EQUIVALENT` | Custo equivalente à vista |

## Escopos

| Escopo | Conjunto do ranking |
|--------|---------------------|
| `BEST_PER_DISTRIBUTOR` | Melhor oferta elegível por distribuidora |
| `ALL_OFFERS` | Todas as ofertas elegíveis |

## Desempate (ordem)

1. Custo do modo selecionado
2. Custo equivalente
3. Custo entregue
4. Preço bruto
5. Entrega mais rápida
6. Maior validade restante
7. Ativação mais recente
8. Nome da distribuidora
9. ID do item

## Contadores do resumo

- `eligible_count`: ofertas `ELIGIBLE`
- `warning_count`: ofertas `ELIGIBLE_WITH_WARNINGS`
- `ineligible_count`: ofertas `INELIGIBLE`

Inelegíveis não recebem `rank_position`.
