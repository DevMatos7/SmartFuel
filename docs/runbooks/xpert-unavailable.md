# Runbook — XPERT unavailable

**Sintoma:** sync falha / conexão indisponível.  
**Impacto:** dados desatualizados; dashboards com freshness STALE/NOT_SYNCED.  
**Mitigação:** não escrever no XPERT; abrir alerta `SOURCE_UNAVAILABLE`; sync manual só se ADMIN + fonte homologável.  
**Encerrar:** conexão restaurada + sync bem-sucedido.
