# Custo equivalente à vista

## Taxa diária

```
taxa_diária = (1 + taxa_anual_efetiva) ^ (1 / base_dias) - 1
```

Base padrão: 365 dias. Não usar divisão simples da taxa anual.

## Custo equivalente

```
custo_equivalente =
  custo_entregue / (1 + taxa_diária) ^ dias_financeiros
```

## Dias financeiros

- À vista / antecipado: `0`
- A prazo: `payment_term_days_snapshot`

## Taxa zero

Quando `annual_effective_rate = 0`, o equivalente é igual ao custo entregue.

## Ausência de parâmetro

- Modos `RAW` e `DELIVERED`: continuam funcionando
- Modo `FINANCIAL_EQUIVALENT`: motivo `MISSING_FINANCIAL_PARAMETER`

## Resolução histórica

O parâmetro é resolvido pela vigência em `comparison_datetime`, não pelo estado `active` atual.
