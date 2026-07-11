# Sprint 8.1 — Descoberta de comparabilidade + homologação

> Fase autorizada após aprovação da fundação da Sprint 8.  
> Etapas de 7 e 30 dias de benchmark em lote: **bloqueadas** até aprovar uma compra real.

---

## Decisão formal (esta fase)

| Item | Status |
|------|--------|
| Sprint 8 — fundação | APROVADA (prévia) |
| Sprint 8.1 — matriz de descoberta | **EXECUTADA** |
| `REAL_COMPARABLE_PURCHASES` | **0** |
| Homologação com compra real | **BLOQUEADA por dados** (não por código) |
| Teste E2E no-hindsight | **PASSANDO** |
| Etapa 7 dias / 30 dias | **BLOQUEADAS** |
| Sprint 7.2 / Sprint 9 | Inalteradas (adiada / não autorizada) |

---

## 1. Matriz de cobertura potencial

Script: `backend/scripts/homolog_sprint81_discovery.py` (somente leitura).

Artefatos:

- `docs/sprints/sprint-08-1-discovery-30d.json` / `.md`
- `docs/sprints/sprint-08-1-discovery-90d.json` / `.md`

### Resumo 90 dias (2026-04-12 → 2026-07-11)

| Métrica | Valor |
|---------|-------|
| Grupos nota×produto analisados | 2 |
| Tecnicamente comparáveis | 0 |
| **REAL_COMPARABLE_PURCHASES** | **0** |
| Motivo dominante | `UNMAPPED_PRODUCT` (2) |

### Inventário do PostgreSQL de homologação

| Entidade | Qtd |
|----------|-----|
| Notas de compra | 4 |
| Itens de compra | 2 |
| Itens com produto canônico mapeado | 0 |
| Cotações com `activated_at` | 0 |

### Linhas da matriz (90d)

| Nota | Posto | Ref | Conf | Produto | Vol | Real/L | Cotações&lt;T | Elegíveis | Motivo |
|------|-------|-----|------|---------|-----|--------|--------------|-----------|--------|
| 83471 | Matriz homolog | 2026-07-09T00:00Z | MEDIUM | — (ERP 1505) | 0 | — | 0 | 0 | UNMAPPED_PRODUCT |
| 83471 | Matriz homolog | 2026-07-09T00:00Z | MEDIUM | — (ERP 1506) | 0 | — | 0 | 0 | UNMAPPED_PRODUCT |

Observações honestas:

- Volume em litros = 0 nos itens sincronizados (sem conversão/mapeamento).
- Sem `canonical_product_id`, o motor histórico de cotações não tem produto para cruzar.
- Não há cotações ativas no PG; mesmo com mapeamento, hoje não haveria candidato histórico.
- **Não foi inventada nem retroagida cotação** para forçar comparabilidade.

### Conclusão da Etapa 1

Não existe compra real comparável no período controlado.  
A homologação real da Sprint 8 permanece pendente por **disponibilidade de dados** (mapeamento produto + volume + cotações históricas anteriores a T).

---

## 2. Teste E2E no-hindsight

Arquivo: `backend/tests/test_purchase_benchmark_no_hindsight_e2e.py`

Cenário:

| Cotação | `activated_at` vs T=2026-07-09 10:00Z | Resultado |
|---------|----------------------------------------|-----------|
| A | antes, elegível, preço alto | candidata, não melhor |
| B | **depois** de T | **ausente** do conjunto histórico |
| C | antes, volume mínimo 20 000 L (compra 4 000) | candidata **INELIGIBLE** (`MINIMUM_VOLUME_NOT_REACHED`) |
| D | antes, elegível, melhor preço | **selecionada** (`is_best`, rank 1) |

Pipeline atravessado: compra → agrupamento → referência (override HIGH em T) → `QuoteEvaluationService` → ranking → item → candidatos → snapshot → hash → reprocessamento.

Resultado da execução (container backend + `postgres_test`):

```text
PASSED tests/test_purchase_benchmark_no_hindsight_e2e.py::test_purchase_benchmark_no_hindsight_e2e
```

Reprocessamento no mesmo teste: `run_id` diferente, `reprocess_of_run_id` preenchido, `snapshot_hash` igual, run original intacta.

Correção colateral no orquestrador: flush do `benchmark_item` **antes** de persistir candidatos (evita FK quebrada). Parâmetros de tolerância passam a resolver em **T** (`reference_datetime`), não em `now`.

---

## 3. Benchmark de compra real

**Não executado.** Pré-condição `REAL_COMPARABLE_PURCHASES >= 1` não satisfeita.

Quando existir ao menos uma compra comparável (produto combustível mapeado, volume &gt; 0, custo entregue, referência, cotação histórica elegível sem hindsight), a Etapa 3 deve produzir:

- evidências da compra e da referência;
- lista completa de candidatos históricos;
- cálculos manuais de variance / opportunity / advantage;
- `MAX(candidate.activated_at) <= reference_datetime`;
- reprocessamento imutável.

---

## 4. Pendências fora do escopo 8.1 (ainda abertas para fechar Sprint 8)

Conforme revisão da fundação — **não** bloqueiam a descoberta, mas bloqueiam o aceite final da Sprint 8:

1. APIs `trend` / `by-station` / `by-product` / `by-distributor` (última run válida por nota)
2. UI administrativa de parâmetros (nova vigência)
3. Exportações só a partir de snapshots
4. Vitest das telas novas
5. Suítes completas + `npm run build` + Alembic em banco vazio/teste

---

## 5. Próximos passos recomendados (dados)

Para desbloquear a Etapa 3 sem inventar cotação:

1. Mapear produtos ERP das notas de combustível → canônicos (`fuel_family` + unidade litros).
2. Garantir `volume_liters` &gt; 0 nos itens de combustível.
3. Ter ao menos uma cotação **ativada antes de T** da compra, no mesmo posto/produto, com volume elegível.
4. Preferencialmente mapear fornecedor ERP → distribuidora.
5. Reexecutar `homolog_sprint81_discovery.py 30` (ou 90) e, se `REAL_COMPARABLE_PURCHASES >= 1`, autorizar benchmark de **uma** nota.

Até lá: validação sintética via E2E; homologação real **pendente**.
