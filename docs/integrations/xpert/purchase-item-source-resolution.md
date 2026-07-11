# Resolução de origem dos itens de compra (rascunho pós-perfil)

> Documento vivo da Sprint 8.3. A política definitiva só fecha após matching homologado no dia único.

## Fontes

| Fonte | Tabela XPERT | Papel |
|-------|--------------|--------|
| Movimento físico | `ITENSMOVPRODUTOS` (via `MOVPRODUTOS`) | Quantidade física / estoque |
| Item fiscal | `ITENSCOMPROVANTE` | Documento fiscal, CFOP, tributos, valores de item |

## Evidência do perfil (filial 2443)

- Toda nota de entrada na janela 7/30/90d tem linhas fiscais.
- Só ~27–31% das notas têm movimento físico.
- Volume LT de combustível (produtos 1/2/4/1271/1272) **coincide** entre MOV e FISCAL no agregado.
- Há mais linhas fiscais que físicas → risco de dupla contagem / granularidade tributária se fizer `UNION ALL`.

## Chaves

- Nota: `ID_COMPROVANTE`
- Fiscal: `ID_ITENSCOMPROVANTE` · sequência candidata `DFE_NITEM` (**não comprovada** vs movimento)
- Movimento: IDs de `MOVPRODUTOS` / `ITENSMOVPRODUTOS` conforme contrato atual

## Precedência proposta

1. **Volume:** movimento físico válido; fiscal só como fallback controlado.
2. **Fiscal:** CFOP, desconto/frete/seguro/outras por item, ICMS/ST/FCP.
3. **Custo:** `commercial_delivered_cost` (Sprint 7); registrar `cost_source` / `volume_source`.
4. **Ambiguidade:** status `AMBIGUOUS_SOURCE_MATCH` — não escolher arbitrariamente.

## Proibições

- `UNION ALL` sem identidade.
- Fallback fiscal com unidade UN/PC/CX/KG/TON sem fator explícito.
- Usar cotações `SYNTHETIC_TEST` / `analytics_eligible=false` em benchmark real.

## Próximo passo

Implementar contratos `FUEL_PURCHASE_ITEMS_MOVEMENT` e `FUEL_PURCHASE_ITEMS_FISCAL`, matching e sync do dia **2026-06-20**.
