# Semântica temporal

Campos distintos por observação:

| Campo | Significado |
|-------|-------------|
| `observation_datetime` | Data/hora econômica da série |
| `reference_period_start/end` | Período de referência (ex.: semana CEPEA) |
| `published_at` | Quando a fonte publicou |
| `available_at` | Quando ficou disponível |
| `fetched_at` | Quando o sistema coletou |

**Proibido** usar `fetched_at` como data econômica.

Frequências: INTRADAY, DAILY, WEEKLY, MONTHLY, IRREGULAR.

O banco **não** cria observações artificiais para dias sem publicação.

A Sprint 10 consome `available_at` (não apenas `observation_datetime`) para impedir hindsight nas análises de associação.

