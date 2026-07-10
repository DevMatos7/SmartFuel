# Checkpoints XPERT

## Escopo

Um checkpoint por combinação:

```
erp_source_id + erp_dataset_id + station_id
```

`station_id` nulo representa escopo global (ex.: datasets futuros). Unicidade garantida por `UNIQUE NULLS NOT DISTINCT` (migration 0010).

## Tipos

| Tipo | Uso |
|------|-----|
| `NONE` | Full sem estado incremental |
| `TIMESTAMP` | Valor datetime da última janela bem-sucedida |
| `ID` | Último ID processado |

## Avanço atômico

O checkpoint só avança após:

1. Extração concluída
2. Staging e validação crítica
3. Aplicação dos registros válidos
4. Inativação por ausência (somente full completo)
5. Contadores persistidos
6. Run marcada `COMPLETED`

## Reset administrativo

Apenas `ADMIN`, com motivo obrigatório e confirmação.

- **CLEAR**: remove checkpoint; próxima execução será full.
- **Novo valor**: redefine manualmente (reprocessamento controlado).

⚠️ Reset incorreto pode reprocessar ou inativar dados indevidamente.

## Runs abandonadas

Worker sem heartbeat além do limite marca run como `FAILED_WORKER_LOST`. Checkpoint não avança. Retry cria nova run.
