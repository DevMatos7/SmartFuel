# Ingestão de XML NF-e

## Achado XPERT (Sprint 7.1)

O SQL Server **não armazena o arquivo XML**.

Tabela `COMPENTRADAS` (evidência: `Dados CHAVE XML.txt`):

| Coluna | Uso no Smart Fuel |
|--------|-------------------|
| `CHAVEACESSONFE` | `access_key` (44 dígitos) |
| `VLRFRETE` / `VLRSEGURO` / `VLROUTROS` | despesas do cabeçalho |
| `IMPORTOU_XML` | `xml_imported_in_erp` — **flag**, não arquivo |
| `ID_COMPROVANTE` | vínculo com a nota |

### Semântica (obrigatória na UI/API)

| Rótulo | Fonte |
|--------|--------|
| XML importado no ERP | `xml_imported_in_erp` |
| Arquivo XML disponível no sistema | registro em `nfe_xml_documents` com objeto no MinIO |

Não exibir “XML disponível” só com a flag do XPERT.

## Entradas fiscais vs estoque

`Entradas NF.txt` usa `ITENSCOMPROVANTE` (itens fiscais da NF).

`entradas_estoque.sql` / pipeline 7.1 usa `ITENSMOVPRODUTOS` (movimento de estoque).

São camadas distintas; não misturar sem contrato explícito.

## Abstração

`NfeXmlSource` permanece fail-closed até configurar origem externa do arquivo.
