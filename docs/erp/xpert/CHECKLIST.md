# BRIEF técnico + checklist XPERT

Documento de alinhamento antes da modelagem física definitiva e da Sprint 5 (conector).

## 1. Decisões fechadas

| Tema | Decisão |
|------|---------|
| Produto | Inteligência Auto Postos (interno) |
| ERP | XPERT ATX |
| Banco ERP | SQL Server 2022 |
| Escopo inicial | 4 postos (1 matriz + 3 filiais) |
| Bandeira | 2 WHITE_LABEL + 2 SHELL |
| Combustíveis base | Etanol, Gasolina C, Diesel S10, Diesel S500 (+ variantes comum/aditivado) |
| Volume mínimo | 5.000 L **por produto** |
| Cotações | WhatsApp + Portal (MVP: manual + evidência) |
| Banco da app | PostgreSQL |
| Deploy | Docker em servidor próprio; preparação para VPS Linux |
| Escrita no XPERT | Proibida |

## 2. Cobertura atual das queries

### Já disponíveis

| Fonte | Arquivo | Cobre |
|-------|---------|-------|
| Faturamento / vendas | `queries/faturamento.sql` | Volume, preço, desconto, custo, lucro, forma pgto, frentista |
| Contas a pagar (abertos) | `queries/contas_pagar.sql` | Títulos pendentes + baixas parciais |
| Contas a receber (abertos) | `queries/contas_receber.sql` | Liquidez / pendências |
| Produtos | `queries/produtos.sql` | Cadastro, grupo, similares, preços locais |
| Estoque atual | `queries/estoque.sql` | QTDEATUAL por produto/local |
| Posição atual | `queries/posicao_atual_produtos.sql` | Snapshot produto + custo médio + VALOR1 |
| Preço de venda (lista) | `queries/preco_venda.sql` | VALOR1..4 + estoque + custo |
| Preço praticado por dia | `queries/preco_produtos_por_dia.sql` | Faixas de preço realizadas nas vendas |
| Entradas de estoque | `queries/entradas_estoque.sql` | Movimentos de entrada (CFOP, qtde, custo, fornecedor, NF) |
| Clientes/fornecedores | `queries/entidades.sql` | Cadastro entidades (exclui só cliente) |

### Lacunas críticas

1. **Pedido de compra** (cabeçalho + itens) — tabela ainda não documentada.
2. **Chave de acesso NF-e** — confirmar coluna em `COMPROVANTES` ou tabela fiscal.
3. **Histórico explícito de alteração de preço de bomba** (quem/quando alterou VALORn) — hoje há preço atual e preço praticado nas vendas; falta log de mudança cadastral se existir.
4. **Capacidade de tanque / inventário físico** — se houver no XPERT.
5. **Contas a pagar liquidadas** — a query atual filtra `DTAPGTO IS NULL`.
6. **Domínio completo de `SAIDAS_ENTRADAS` e CFAPs** usados para combustível.
7. **Significado de VALOR1..VALOR4** por forma de pagamento.
8. **Mapeamento ID_FILIAL ↔ CNPJ/posto físico** e qual instância SQL Server cada filial usa.
9. **Confirmação de tipo de CFOP** (numérico vs texto) e filtro seguro para vendas de combustível.

## 3. Achados relevantes das novas queries

### Entradas ≈ compras efetivas (parcial)

`Entradas de Estoque` usa `COMPROVANTES.SAIDAS_ENTRADAS IN (1,9,21)` sobre as mesmas tabelas de movimento (`MOVPRODUTOS` / `ITENSMOVPRODUTOS` / `COMPROVANTES`). Isso **desbloqueia custo de aquisição e volumes entrados** mesmo sem pedido formal, mas:

- Não substitui pedido de compra (intenção vs realizado).
- Chave NF-e / XML ainda precisam ser localizados.
- Frete e condição de pagamento podem estar em outras tabelas.

### Preço por local de venda

`PRODUTOSPORLOCALVENDA` + `LOCALVENDAS` + `VALOR1..4` alimentam o módulo de precificação (Sprint 11) e dashboards de preço.

### Produtos não mapeados

Descrições variam por filial; `erp_product_mappings` (Sprint 2) é obrigatório antes do BI consolidado.

### Entidades

`Cliente_Fornecedor <> 1` na query de cadastro — confirmar encoding (1 = só cliente?). Distribuidores entram via `ENTIDADES` + uso em entradas / contas a pagar.

## 4. Arquitetura de sincronização (alvo)

| Informação | Frequência sugerida |
|------------|---------------------|
| Cotações | Imediata (app) |
| Vendas | 10 min |
| Preços de venda | 5 min |
| Estoque | 15 min |
| Entradas / NF | 15 min |
| Contas a pagar | 30 min |
| Índices externos | Diário |

Estratégia: checkpoint por ID / data; staging + upsert idempotente.

## 5. Checklist de solicitação ao time XPERT

Para cada item: **nome da tabela**, **colunas-chave**, **exemplo de SELECT**, **filtro por filial**, **índices existentes**.

- [ ] Pedido de compra + itens (número, data, fornecedor, status, volumes, preço negociado)
- [ ] Vínculo pedido ↔ comprovante/NF
- [ ] Campo/chave NF-e e local do XML
- [ ] Frete, desconto e impostos na entrada
- [ ] Condição / prazo de pagamento na compra
- [ ] Baixas históricas de contas a pagar (incluindo liquidados)
- [ ] Log de alteração de preço (`VALOR1..4`) se existir
- [ ] Tanques: capacidade, produto ligado, inventário
- [ ] Dicionário `SAIDAS_ENTRADAS` e status de item (`STATUS <> 2`)
- [ ] Lista oficial de CFOPs de venda/compra de combustível
- [ ] Significado de `VALOR1`–`VALOR4`
- [ ] Relação `ID_FILIAL` × CNPJ × servidor SQL
- [ ] Usuário SQL read-only por instância (sem `sa`)

## 6. Próximos passos de produto

1. Sprint 0 (fundação) — este repositório.
2. Sprint 1 — org, postos, JWT.
3. Sprint 2 — produtos canônicos + mapeamento ERP.
4. … conforme roadmap em `docs/sprints/`.

Não avançar modelagem física de compras até receber pelo menos chave NF-e + pedido (ou confirmação de que pedido não será usado no MVP e entradas bastam).
