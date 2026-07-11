# Sprint 11 — Formação de preço, margem, aprovação e evidências

**Status:** Fundação + homologação sintética liberadas. Homologação real depende de custo e preço confiáveis.

**Proibições:** escrita no XPERT · alteração automática de bomba · Sprint 13.

Sprint 12: liberada em documento separado (`sprint-12.md`).


## Entregue

- Migration `0022_sprint11_pricing_decisions`
- Models de políticas, runs, items, cenários, decisões, aprovações, evidências, checks
- Motor Decimal (margem, markup, piso, alvo, cenários, guardrails, arredondamento)
- Serviço central + workflow + snapshot hash
- APIs `/pricing/*` e `/analytics/pricing/*`
- Frontend `/pricing/*`
- Testes sintéticos `tests/test_pricing_sprint11.py`
- Docs em `docs/pricing/`

## Homologação

- **Etapa A (sintética):** liberada (`POST /pricing/homologation/synthetic`)
- **Etapa B/C real:** bloqueada até custo/preço confiáveis + autorização operacional

## Confirmações

- Sem escrita no XPERT: `xpert_write_enabled=false`
- Sprint 12: **não antecipada**
