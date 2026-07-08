# Integração XPERT ATX

## Status

Fontes parciais mapeadas a partir de consultas exportadas do ERP. A integração de runtime começa na **Sprint 5**. Nesta Sprint 0 apenas versionamos as queries e o checklist.

## Regras

- Usuário SQL **somente leitura**.
- Consultas parametrizadas; sem datas fixas em produção.
- Nunca inventar nomes de tabelas/colunas sem evidência no ERP.
- Credenciais apenas em variáveis de ambiente / secrets.

## Filiais conhecidas nos scripts

`12290`, `5301`, `16709`, `2443` (e variações em produtos como `16719` — confirmar se é a mesma filial).

## Tabelas já citadas nas consultas

| Área | Tabelas |
|------|---------|
| Vendas / movimentos | `MOVPRODUTOS`, `ITENSMOVPRODUTOS`, `COMPROVANTES`, `FILIAIS` |
| Produtos | `PRODUTOS`, `GRUPOPRODUTOS`, `PRODUTOSPORLOCALVENDA`, `PRODUTOSSIMILARES`, `LOCALVENDAS` |
| Estoque | `ESTOQUE` |
| Entidades | `ENTIDADES`, `CIDADES`, `EMPRESASENTIDADES`, `LISTANEGRACLIENTES` |
| Financeiro | `CONTASPAGAR`, `CONTASPAGARBAIXA`, `CONTASRECEBER`, `CONTASRECEBERBAIXA` |
| Pessoas / acesso | `FUNCIONARIOS`, `USUARIOS` |
| Config | `CFGGERAL` |

## Classificação de movimento (`COMPROVANTES.SAIDAS_ENTRADAS`)

| Valor observado | Uso |
|-----------------|-----|
| `0` | Saídas / vendas (preço por dia) |
| `1, 9, 21` | Entradas de estoque (compras/outras entradas) |

Confirmar no XPERT o significado completo do domínio.

## Preço de venda

`PRODUTOSPORLOCALVENDA.VALOR1..VALOR4` — preços por local/forma. Mapear o significado de cada `VALOR` (dinheiro, cartão, etc.) com o time do posto.

## Queries versionadas

Ver pasta [`queries/`](./queries/).

## Checklist pendente (time XPERT)

Ver [`CHECKLIST.md`](./CHECKLIST.md).
