# Sincronização incremental XPERT

## Janela por timestamp

Modo `INCREMENTAL_TIMESTAMP`:

```
[checkpoint - overlap_seconds, source_upper_bound)
```

- Limite inferior **inclusivo**.
- Limite superior **exclusivo**.
- `source_upper_bound` obtido do SQL Server (`SELECT SYSUTCDATETIME()` ou equivalente), **não** de `datetime.now()` do backend.
- Datas normalizadas em UTC; timezone da origem aplicado quando configurado.

## Registro na fronteira superior

Registro com `source_updated_at = source_upper_bound` fica para a próxima janela.

## Overlap

`overlap_seconds` (padrão 300) garante reentrada segura após falhas parciais. Hashes no staging evitam duplicidade na reaplicação.

## Checkpoint

Após `COMPLETED` sem cancelamento:

- checkpoint avança para `source_upper_bound`;
- em `PARTIAL`, `FAILED`, `CANCELLED` ou `FAILED_WORKER_LOST`, checkpoint **permanece**.

## Modo por ID

`INCREMENTAL_ID` exige ID monotônico na origem. Não habilitar para PRODUCTS/SUPPLIERS sem evidência de que registros antigos não são alterados.

## Primeira execução

Agenda incremental exige full inicial concluída com sucesso para o escopo (fonte + dataset + posto).
