# Sprint 10 — Correlação, defasagem e índice de repasse

Status: **fundação + motor sintético entregues**  
Homologação real: **bloqueada** até séries externas da Sprint 9 homologadas  
Sprint 11: **NÃO AUTORIZADA / NÃO IMPLEMENTADA**

## Decisão formal

| Item | Status |
|------|--------|
| Desenvolvimento estrutural | Liberado |
| Homologação sintética | Liberada |
| Homologação real | Condicionada à Sprint 9 + amostra |
| Causalidade | **Proibida** na UI/relatórios |
| Motor | Somente PostgreSQL (sem XPERT) |
| Migration | **`0021_sprint10_market_correlation`** (após `0020`) |

## Entregas

### Modelos
- `market_analysis_parameters`
- `market_analysis_runs` (+ snapshot hash imutável)
- `market_analysis_results`
- `market_aligned_observations`
- `market_pass_through_events`
- `internal_market_series_points`

### Motor
- Alinhamento com `available_at <= T` (no-hindsight)
- Transformações: LEVEL, ABSOLUTE_CHANGE, PERCENTAGE_CHANGE, BASE_100
- Pearson + Spearman
- Cross-correlation por lag configurável
- Repasse absoluto / elasticidade
- Assimetria alta × queda
- Qualidade estatística (amostra, série constante, denominador pequeno)
- Reprocessamento cria nova run

### APIs
- `/api/v1/market-analysis/*`
- `/api/v1/analytics/market-correlation/*`

### Frontend
- `/analytics/market-correlation`
- Detalhe da run, qualidade, parâmetros
- Botão de cenário sintético (lag ~3)

### Linguagem obrigatória
- associação observada
- defasagem estimada
- repasse observado
- amostra insuficiente

## Pendências

- Builder completo de séries internas a partir de cotações/compras/vendas reais
- Proxy Brent×dólar materializado
- PDF executivo rico
- Vitest das telas
- Homologação CEPEA/Brent/dólar após Sprint 9

## Confirmação

**Sprint 12:** fundação liberada — ver [sprint-12.md](./sprint-12.md). Sprint 13 **não autorizada**.

**Sprint 12 não foi antecipada na Sprint 11.**
