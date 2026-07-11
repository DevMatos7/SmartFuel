# Sprint 8 — Compra real × melhor cotação

Status: **fundação aprovada; prontidão de dados em andamento (8.2/8.3)**

## Decisões formais

| Item | Status |
|------|--------|
| Sprint 7.2 XML | **ADIADA** (estruturas mantidas) |
| Pipeline compras 7.1 | Mantido; itens em revisão na **8.3** |
| Sprint 8 / 8.1 | Fundação + discovery **aprovadas** |
| Sprint 8.2 Etapa A | **APROVADA** (sync 7d cabeçalhos/títulos) |
| Sprint 8.3 Etapa A | **CONCLUÍDA** (perfil MOV × FISCAL) |
| Sprint 8.3 Etapa B | **PENDENTE** — dia `2026-06-20` + origem canônica |
| Fonte XPERT | UNSAFE — sa; agenda bloqueada; produção bloqueada |
| Benchmark real | **BLOQUEADO** até compra pós-cotação operacional |
| Sprint 9 | **NÃO AUTORIZADA** |

## Entregas

- Models + migration `0018_sprint8_benchmarks`
- Orquestrador `PurchaseQuoteBenchmarkService` (reusa motor Sprint 4)
- APIs runs / invoice / analytics / export / overrides / parâmetros
- Telas dashboard, oportunidades, qualidade, detalhe da run, aba na nota
- Docs de metodologia
- Sprint 8.3: migration `0019_sprint83_quote_origin` (`quotes.origin`, `analytics_eligible`)

## Homologação

- Etapa A: testes sintéticos (unitários de agrupamento/fórmulas) — ok
- Etapa B: uma compra real comparável (produto L + mapeado + cotação histórica) — **bloqueada** (sem cotação anterior válida)
- Carga combustível LT: aguarda Sprint 8.3 Etapa B
- Etapa C/D: sete / trinta dias — após B

## Fora de escopo

XML, Sefaz, índices externos, IA, pedido automático, Sprint 9.
