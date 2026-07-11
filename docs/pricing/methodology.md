# Metodologia — Formação de preço (Sprint 11)

## Princípios

- **Recomendação ≠ preço aprovado ≠ preço implantado.**
- A Sprint 11 **não escreve no XPERT** e não altera preço de bomba.
- Nomenclatura: **margem bruta comercial estimada** (não é lucro líquido, DRE nem resultado contábil).
- **Sem hindsight:** só entram dados com `available_at <= T` no momento de referência.
- **Custo ausente nunca vira zero** → `MISSING_COST` → `NO_RECOMMENDATION`.

## Fluxo

```
política + custo + preço vigente (+ sinal de mercado opcional)
  → margem / piso / alvo / cenários
  → guardrails + arredondamento
  → recomendação + snapshot imutável
  → decisão humana → aprovação → implantação externa → comprovação
```

## Tipo de preço homologado

Enquanto formas de pagamento da Sprint 6 não estiverem homologadas: **somente `POSTED_PRICE`**.

## Sinais de mercado (Sprint 10)

Consultivos. Não aplicam multiplicador automático. Qualidade insuficiente não altera o cálculo numérico.
