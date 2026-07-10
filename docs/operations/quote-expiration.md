# Expiração de cotações

## Objetivo

Garantir que cotações vencidas não permaneçam utilizáveis como ativas (RDC-016, RDC-017).

## Mecanismos

### 1. Status efetivo (runtime)

A API calcula `effective_status` em respostas. Cotação `ACTIVE` com `valid_until <= UTC now` é tratada como expirada mesmo antes do job.

### 2. Job de expiração

```
POST /api/v1/quotes/expiration/run
```

- Permissão: `quote_expiration.execute` (ADMIN)
- Idempotente: reexecução não gera efeitos colaterais em cotações já finalizadas
- Persiste `EXPIRED`, registra histórico com ação `EXPIRED`

## Configuração

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `QUOTE_EXPIRATION_INTERVAL_MINUTES` | 15 | Intervalo sugerido para agendamento externo |

## Agendamento

Não há cron embutido nesta sprint. Opções:

1. **Cron do host** ou scheduler (Kubernetes CronJob, etc.) chamando o endpoint com token ADMIN
2. **Execução manual** em ambientes de desenvolvimento

Exemplo (desenvolvimento):

```bash
curl -X POST http://localhost:8000/api/v1/quotes/expiration/run \
  -H "Authorization: Bearer <token_admin>"
```

## Regras

- Apenas cotações `ACTIVE` são candidatas
- `CANCELLED` e `SUPERSEDED` não são alteradas
- Itens com `valid_until` próprio podem expirar antes do cabeçalho; a cotação expira integralmente quando a validade geral vence ou todos os itens estão vencidos (conforme implementação do serviço)

## Monitoramento sugerido

- Logar quantidade de cotações expiradas por execução
- Alertar se job não executar por > 2× o intervalo configurado
