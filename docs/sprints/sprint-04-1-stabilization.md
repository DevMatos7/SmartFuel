# Sprint 4.1 — Estabilização do Motor de Comparação

## Objetivo

Fortalecer reprodutibilidade, consistência temporal, cobertura de testes e documentação antes da Sprint 5.

## Entregas

### Contexto imutável
- `CandidateEvaluationContext` e `QuoteEvaluationService`
- Regra comercial resolvida uma única vez por candidato

### Resolução histórica
- Regras: vigência em `comparison_datetime`, `historical=True` ignora `active`
- Taxas: `find_effective(historical=True)` por vigência

### Snapshot e hash
- Serialização canônica em `snapshot_canonical.py`
- Hash SHA-256 determinístico sobre cenário + resultados

### Exportações
- PDF/CSV usam `distributor_name` do snapshot

### Atomicidade
- Avaliação em memória antes de persistir resultados
- Status `FAILED` em falhas com mensagem sanitizada

### Migration
- `0008_sprint41_stabilization`: exclusion constraint em parâmetros financeiros

### Testes
- `test_quote_comparison_domain.py` — 16 testes unitários
- `test_sprint41_stabilization.py` — 7 testes de integração

## Pendências remanescentes (backlog)

- Alternância de modo/escopo sem nova requisição no frontend
- Extração de componentes visuais
- Campo `deactivated_at` explícito em regras (semântica documentada via vigência)

## Sprint 5

Não antecipada nesta estabilização.
