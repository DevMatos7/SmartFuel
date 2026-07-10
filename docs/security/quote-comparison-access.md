# Acesso à comparação de cotações

## Permissões

| Permissão | Descrição |
|-----------|-----------|
| `quote_comparisons.read` | Visualizar comparações |
| `quote_comparisons.run` | Executar comparação |
| `quote_comparisons.export` | Exportar PDF/CSV |
| `quote_comparisons.reprocess` | Reprocessar cenário |
| `quote_comparisons.view_calculation` | Memória de cálculo |

| Permissão | Descrição |
|-----------|-----------|
| `financial_parameters.read` | Consultar taxas |
| `financial_parameters.write` | Criar taxas |
| `financial_parameters.deactivate` | Inativar taxas |

## Escopo por posto

Toda execução valida acesso ao `station_id` informado. Listagens respeitam postos autorizados do usuário.

## Exportações

PDF e CSV usam dados do snapshot persistido, não cadastros atuais de distribuidoras ou produtos.

## Perfil CONSULTA

Pode ler e exportar comparações concluídas, mas não executar nem reprocessar.
