# Migração futura — agente remoto (VPS)

## Contexto

Hoje o conector usa `DirectSqlServerDataSource` no mesmo ambiente Docker (backend/worker) com acesso de rede ao SQL Server do cliente.

Em instalações onde o SQL Server não é exposto à internet, a arquitetura prevê um **Remote Agent** na VPS ou rede local do posto.

## Fora do escopo Sprint 5.1

- Agente remoto
- VPN automatizada
- CDC / Change Tracking nativo

## Diretriz arquitetural

1. API e worker continuam no PostgreSQL central.
2. Agente local executa apenas consultas aprovadas (somente leitura).
3. Credenciais permanecem em `secret_ref`; agente recebe token de curta duração.
4. Staging e checkpoints permanecem no PostgreSQL; agente envia lotes assinados.

## Preparação atual

- Queries versionadas no repositório
- Contratos e `query_hash`
- Worker desacoplado do FastAPI
- Documentação de secrets em `security.md`

Quando o agente for implementado (backlog), reutilizar os mesmos contratos e normalizadores.
