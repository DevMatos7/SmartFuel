# Sprint 9 — Índices externos e inteligência de mercado

Status: **fundação implementada** · homologação em andamento  
Sprint 10 (correlação/repasse): **NÃO AUTORIZADA / NÃO IMPLEMENTADA**

## Decisão formal

| Item | Status |
|------|--------|
| Objetivo | Coleta + normalização + qualidade + visualização |
| Correlação / repasse / previsão | **Fora de escopo** |
| Scraping / CAPTCHA bypass | **Proibido** |
| CSOnline | `MISCONFIGURED` até contrato autorizado |
| Scheduler | Bloqueado até homologação completa |
| Sprint 8 | Permanece em homologação (independente) |
| Head Alembic anterior | `0019_sprint83_quote_origin` |
| Migration | **`0020_sprint9_external_indices`** |

## Entregas

### Dados
- `external_data_sources`
- `external_series`
- `external_observations` (revisões CURRENT/SUPERSEDED)
- `external_ingestion_runs`
- `external_import_files`
- `external_quality_issues`

### Serviços
- Adaptadores: Manual, CSV, XLSX, API, AuthorizedWeb
- Unidades/conversões explícitas (`forbid_auto_currency`)
- Observações versionadas + hash canônico
- Freshness por frequência
- Import CSV com preview → confirmação
- Catálogo padrão: Brent, USD/BRL, CEPEA MT, CSOnline

### APIs
- `/api/v1/external-data/*`
- `/api/v1/analytics/external-indices/*`

### Frontend
- Dashboard, séries, detalhe, fontes, importação, runs, qualidade
- Rota: `/analytics/external-indices`

### Permissões
- `external_data.read|import|sync|manage_sources|manage_series|manage_schedule|resolve_quality|view_raw|export`

## Homologação

| Etapa | Conteúdo | Status |
|-------|----------|--------|
| A | Estrutura + import manual | Pronta para executar |
| B | Brent / dólar | Via import/manual |
| C | CEPEA semanal | Frequência preservada |
| D | CSOnline | Bloqueada (sem contrato) |
| E | Backfill 30/90/365 | Controlado, sob demanda |

## Documentação relacionada

- `docs/external-data/source-adapters.md`
- `docs/external-data/time-semantics.md`
- `docs/external-data/units-and-conversions.md`
- `docs/external-data/revisions.md`
- `docs/external-data/freshness.md`
- `docs/external-data/manual-import.md`

## Confirmação

**Sprint 10 não foi antecipada.** Não há correlação, índice de repasse, previsão nem recomendação de compra.
