# Contrato FUEL_SALES_ITEMS — XPERT

## Hub de replicação (multi-filial)

A conexão SQL Server de homologação concentra dados **replicados de todas as unidades** no mesmo banco (`atxdados`). Toda query de dataset por posto **deve** filtrar por `ID_FILIAL = @station_erp_id`, mapeado em `stations.erp_branch_id`.

Joins entre tabelas devem incluir `ID_FILIAL` e `ID_DB` quando aplicável, para evitar cruzamento entre filiais.

Filiais conhecidas na rede: `12290`, `5301`, `16709`, `2443` (Matriz homologação).

## Origem

Query versionada: `backend/app/integrations/xpert/queries/fuel_sales_items.sql`

Base analítica: [`docs/erp/xpert/queries/faturamento.sql`](../../erp/xpert/queries/faturamento.sql)

## Tabelas utilizadas

| Tabela | Papel |
|--------|-------|
| `ITENSMOVPRODUTOS` | Item de movimento (volume, preço, custo, desconto) |
| `MOVPRODUTOS` | Cabeçalho do movimento (data, forma pagamento) |
| `COMPROVANTES` | Comprovante fiscal (cancelamento, tipo saída/entrada) |

## Chave natural

- `source_sale_id` = `MOVPRODUTOS.ID_MOVPRODUTOS`
- `source_sale_item_id` = `ITENSMOVPRODUTOS.ID_ITENSMOVPRODUTOS`

## Filtros de negócio

- `ID_FILIAL = @station_erp_id`
- `COMPROVANTES.SAIDAS_ENTRADAS = 0` (vendas/saídas)
- `ITENSMOVPRODUTOS.CFOP > '3000'` (mesma regra do faturamento legado)
- Janela incremental: `source_updated_at >= @window_start` (inclusivo) e `< @window_end` (exclusivo)

## Cancelamento

Itens com `COMPROVANTES.CANCELADO = 1` ou `ITENSMOVPRODUTOS.STATUS = 2` são **incluídos** com `source_cancelled = 1` para permitir correções retroativas.

## Devolução

`source_operation_type = RETURN` quando `QTDE < 0`.

## Campos ausentes

- `source_unit` — não preenchido (litros assumidos na normalização quando unidade nula)
- `source_surcharge_amount` — não retornado pelo ERP nesta consulta

## Pendências DBA

1. Confirmar coluna de alteração confiável para incremental (`source_updated_at` usa `MOVPRODUTOS.DATA` / `COMPROVANTES.DTACONTA`)
2. Validar filtro CFOP para todos os combustíveis da rede
3. Confirmar domínio completo de devoluções (`SAIDAS_ENTRADAS`, quantidade negativa)

## Carga histórica inicial

Primeira execução incremental **sem checkpoint** exige `history_start_date` e `history_end_date` na API de sync manual.

## FUEL_RETAIL_PRICES

Query: `fuel_retail_prices.sql` — base `Preço de venda.txt` / `PRODUTOSPORLOCALVENDA`.

Mapeamento provisório `VALORn` → `FORMAPGTO`:

| Coluna ERP | Código FORMAPGTO | Descrição |
|------------|------------------|-----------|
| VALOR1 | 0 | Dinheiro |
| VALOR2 | 4 | Cartão Débito |
| VALOR3 | 1 | à Prazo |
| VALOR4 | 3 | Convênio C/C |

Confirmar com operação antes de produção.
