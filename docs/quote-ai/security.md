# Segurança — Ingestão IA

## Controles de arquivo

`QuoteDocumentSecurityService` valida:

- Extensões: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.txt`, `.csv`, `.xlsx`
- MIME allowlist
- Tamanho (`QUOTE_AI_MAX_FILE_SIZE_MB`, default 10)
- Assinaturas básicas (PDF/PNG/JPEG)
- Bloqueio de executáveis (`MZ`, shebang)

## Permissões

Separadas: `quote_ingestion.read|upload|review|approve|create_draft|retry|archive|view_raw_text|view_ai_payload|manage_provider|run_evaluation|view_costs`.

Texto bruto e payload da IA exigem permissões explícitas.

## Isolamento

- Dados por organização
- Feature flag `quote_ai_ingestion_enabled` obrigatória
- Sem ferramentas de rede/ativação no provedor de extração
- `allow_training_usage=false` por default no provider config

## Canais sensíveis

E-mail e WhatsApp: enums existem; flags `quote_ai_email_channel_enabled` e `quote_ai_whatsapp_channel_enabled` default **false**. WhatsApp não oficial é proibido.
