# Adaptadores de fontes externas

Interface: `ExternalSourceAdapter`

| Adapter | Tipo | Agendamento | Notas |
|---------|------|-------------|-------|
| ManualExternalSourceAdapter | MANUAL | Não | Entrada individual / API manual |
| CsvExternalSourceAdapter | CSV | Não | Via import preview/confirm |
| XlsxExternalSourceAdapter | XLSX | Não | Estrutura pronta; parser completo sob demanda |
| ApiExternalSourceAdapter | API | Sim, após homologação | Exige `contract_validated` + `secret_ref` |
| AuthorizedWebSourceAdapter | AUTHORIZED_WEB | Não | CSOnline: permanece MISCONFIGURED |

Capacidades declaradas: backfill, incremental, revisões, intraday, scheduling, credentials.

**Não** implementar scraping genérico, automação de navegador não autorizada ou bypass de CAPTCHA.
