# Runbook — Sync stuck

**Sintoma:** job `PROCESSING` sem heartbeat.  
**Impacto:** checkpoint parado.  
**Diagnóstico:** `/operations/jobs`, heartbeats.  
**Mitigação:** não cancelar automaticamente sem regra; investigar worker; abrir `SYNC_STUCK`.
