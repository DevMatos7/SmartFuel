# SPRINT 6 — HOMOLOGAÇÃO REAL CONTROLADA

Gerado em: 2026-07-10T09:13 (UTC-4)

Execução manual autorizada em ambiente **não produtivo**, fonte **UNSAFE** (`sa`), hub centralizado `atxdados`.

**Não executado nesta rodada:** carga de 7 dias, carga de 30 dias, homologação de incremental com checkpoint.

---

## 1. Ambiente

| Item | Valor |
|------|-------|
| SQL Server | `192.168.120.253` |
| Banco | `atxdados` |
| Usuário | `sa` (**UNSAFE** — registrado para auditoria) |
| APP_ENV | `development` ✓ |
| XPERT_ALLOW_UNSAFE_PRIVILEGES | `true` ✓ |
| security_status | `UNSAFE` ✓ |
| Execução | Manual por ADMIN (`admin@test.com`) ✓ |
| Agenda automática | **Bloqueada** para fonte UNSAFE ✓ |
| Banner UNSAFE | Exibido no frontend quando `security_status=UNSAFE` |
| Posto | Matriz (`1edc5c8b-0ba1-405c-a000-03e61e31521e`) |
| erp_branch_id | `2443` ✓ |

### Queries — política fail closed

| Verificação | Resultado |
|-------------|-----------|
| Somente SELECT | ✓ (`payment_methods.sql`, `fuel_retail_prices.sql`, `fuel_sales_items.sql`) |
| Hash validado | ✓ (ver seção 2) |
| Exige `@station_erp_id` (vendas/preços) | ✓ |
| `station_id` ausente na validação | **Bloqueado** (`XPERT_STATION_REQUIRED`) |
| `@station_erp_id` ausente na execução | **Bloqueado** (`KeyError` → `XPERT_QUERY_PARAMETER_MISSING`) |
| Filial diferente de 2443 na amostra | **Bloqueado** (`XPERT_BRANCH_ISOLATION_FAILED`) |

---

## 2. Contratos

### PAYMENT_METHODS

| Campo | Valor |
|-------|-------|
| Válido | ✓ |
| Query hash | `6ab184c5a76157b9b92a367360dab4cfa227a28a5d5ce62e2abe2ce9ed69e918` |
| Amostra | 5 linhas / 39 ms |
| `source_branch_id` | N/A (domínio estático FORMAPGTO) |

### FUEL_RETAIL_PRICES

| Campo | Valor |
|-------|-------|
| Válido | ✓ |
| Query hash | `3a3f3b68034b664de99075bf8fa1dbf652d9889209e2e640ce3394a1202f4f7f` |
| Amostra isolamento | 263 linhas / 147 ms |
| Filiais distintas | `['2443']` apenas |
| Chaves duplicadas na amostra | 0 |

### FUEL_SALES_ITEMS

| Campo | Valor |
|-------|-------|
| Válido | ✓ |
| Query hash | `b7978f26def63216b78505bd74d7ac541bb16c7ff201a02a817007a0318f6ff9` |
| Amostra isolamento | 167 linhas (janela 1 dia) / ~11 s |
| Filiais distintas | `['2443']` apenas |
| Chave natural duplicada na amostra | 0 |
| Janela do probe | 1 dia (não 30) |

---

## 3. Isolamento por filial

| Métrica | Resultado |
|---------|-----------|
| Filial esperada | `2443` |
| Filiais em vendas (amostra 500) | `2443` |
| Filiais em preços (amostra 263) | `2443` |
| Linhas de outras filiais | **0** |
| **Resultado** | **APROVADO** |

---

## 4. PAYMENT_METHODS

| Execução | Status | Lidos | Inseridos | Atualizados | Inalterados |
|----------|--------|-------|-----------|-------------|-------------|
| 1ª | COMPLETED | 11 | 0* | 0 | 11 |
| 2ª (idempotência) | COMPLETED | 11 | 0 | 0 | 11 |

\*Dados já existiam de execução anterior; comportamento idempotente confirmado.

| Validação | Resultado |
|-----------|-----------|
| IDs únicos | 11 métodos (`0`–`9`, `16`) |
| Nomes originais preservados | ✓ (ex.: Dinheiro, à Prazo, Cartão Débito) |
| `normalized_group` imposto silenciosamente | **Não** — todos `PENDING` / `UNMAPPED` |
| Duplicidades | 0 |

---

## 5. FUEL_RETAIL_PRICES

| Execução | Status | Lidos | Inseridos | Inalterados |
|----------|--------|-------|-----------|-------------|
| 1ª | COMPLETED | 263 | 0* | 263 |
| 2ª | COMPLETED | 263 | 0 | 263 |

\*Snapshots já existiam; segunda execução não criou duplicatas.

| Validação | Resultado |
|-----------|-----------|
| Snapshots ativos | 263 |
| Combinações únicas (posto+produto+forma) | 263 |
| Duplicidades ativas | **0** |
| Preços > 0 | ✓ |
| Filial | Somente `2443` |

### Mapeamento VALOR1–4 (PROVISÓRIO)

| Coluna | FORMAPGTO | Descrição |
|--------|-----------|-----------|
| VALOR1 | 0 | Dinheiro |
| VALOR2 | 4 | Cartão Débito |
| VALOR3 | 1 | à Prazo |
| VALOR4 | 3 | Convênio C/C |

Registrado no normalizador: `valor_formapgto_mapping_source=LEGACY_REFERENCE`, `valor_formapgto_mapping_status=PROVISIONAL`.

**Não convertido** para grupos canônicos (CASH, DEBIT_CARD, etc.) — aguardando DBA.

---

## 6. Vendas — 1 dia (`2026-07-09`)

| Campo | Valor |
|-------|-------|
| Janela | `2026-07-09` → `2026-07-10` (exclusivo) |
| Sync status | COMPLETED |
| Lidos / aplicados | 552 / 0 (552 inalterados — dados já sincronizados) |
| Erros | 0 |

### Comparação XPERT direto vs PostgreSQL

| Indicador | XPERT (query contrato) | PostgreSQL (elegíveis) | Observação |
|-----------|------------------------|------------------------|------------|
| Itens | 251 | 249 | −2 (1 cancelado + 1 não mapeado) |
| Volume (L) | 7.612,09 | 7.551,08 | −61 L (CFOP 5.667 + não mapeado) |
| Receita líquida | R$ 47.753,06 | R$ 47.264,49 | −R$ 488,57 |
| Descontos | — | R$ 52,05 | |
| Custo | — | R$ 41.830,38 | 100% cobertura nos elegíveis |
| Cancelados | — | 1 item | Excluído dos KPIs |
| Devoluções | 0 | 0 | |
| Chave duplicada | 0 | 0 | |

### CFOP encontrados (XPERT direto, dia 2026-07-09, filial 2443)

| CFOP | Itens | Volume (L) | Valor líquido | Tratamento proposto |
|------|-------|------------|---------------|---------------------|
| 5.656 | 250 | 7.552,08 | R$ 47.317,39 | **Incluir** (venda combustível) |
| 5.667 | 1 | 60,01 | R$ 435,67 | **Revisar com DBA** — possível operação não comercial ou CFOP fora do escopo |

### Analytics (produtos mapeados)

| Métrica | Valor |
|---------|-------|
| Volume | 7.551,08 L |
| Faturamento | R$ 47.264,49 |
| Preço médio | R$ 6,26/L |
| Margem bruta | R$ 5.434,11 (11,5%) |
| Cobertura custo | 100% |
| Não mapeados | 1 item / 1 L |
| Sem custo | 0 |

**Divergência documentada:** diferença entre total da query (251 itens) e KPIs (249) explicada por cancelamento, produto não mapeado e CFOP `5.667` pendente de regra DBA.

---

## 7. Vendas — 7 dias

**NÃO EXECUTADO** — aguardando aprovação formal da etapa de 1 dia.

---

## 8. Vendas — 30 dias

**NÃO EXECUTADO** — conforme protocolo. Execução anterior (fora desta rodada) carregou 30 dias; **não repetida** nesta homologação controlada.

---

## 9. Incremental

**NÃO HOMOLOGADO** nesta rodada.

| Pendência | Estado |
|-----------|--------|
| Coluna `source_updated_at` | Usa `MOVPRODUTOS.DATA` / `COMPROVANTES.DTACONTA` — **confirmar com DBA** |
| Overlap / checkpoint | Teste pendente após aprovação de 7 dias |
| PARTIAL não avança checkpoint | Comportamento implementado ✓ |

---

## 10. Reconciliação

Testada em execução anterior (5 combustíveis mapeados):

- `canonical_product_id` preenchido retroativamente ✓
- Valores originais preservados ✓
- Agregações diárias reprocessadas ✓
- Runs auditados em `sales_mapping_reconciliation_runs` ✓

---

## 11. Pendências e riscos

| Item | Prioridade |
|------|------------|
| CFOP `5.667` e regra `CFOP > '3000'` | Alta — validação DBA |
| Mapeamento VALORn → FORMAPGTO | Alta — provisório |
| Coluna incremental confiável | Alta |
| 11 formas de pagamento pendentes de mapeamento | Média |
| Conta `sa` em produção | **Bloqueado** |
| Sprint 7 | **Não antecipada** |

---

## Gates — resultado

| Gate | Status |
|------|--------|
| APP_ENV != production | ✓ |
| security_status UNSAFE | ✓ |
| XPERT_ALLOW_UNSAFE_PRIVILEGES | ✓ |
| Execução manual ADMIN | ✓ |
| Isolamento filial 2443 | ✓ |
| PAYMENT_METHODS idempotente | ✓ |
| FUEL_RETAIL_PRICES sem snapshot duplicado | ✓ |
| Vendas 1 dia conferidas | ✓ (com ressalvas CFOP) |
| Vendas 7 dias | Pendente |
| Vendas 30 dias | **Não executado** |
| Chave sem duplicidade | ✓ |
| Custo ausente ≠ zero | ✓ |
| Reconciliação | ✓ (execução anterior) |
| Incremental comprovado | Pendente |
| Scheduler bloqueado | ✓ |
| Sprint 7 não antecipada | ✓ |

---

## Scripts de reprodução

```bash
# Provisionar datasets em fonte legada
docker compose exec backend python scripts/bootstrap_xpert_datasets.py

# Homologação controlada (contratos + PAYMENT_METHODS + PREÇOS + 1 dia)
docker compose exec -e HOMOLOG_SALES_DAY=2026-07-09 backend python scripts/homolog_sprint6_controlled.py

# Comparação contábil 1 dia
docker compose exec backend python scripts/homolog_sprint6_day_compare.py 2026-07-09 2443
```

---

## Próximo passo aprovado

1. DBA validar CFOP `5.667` e regra de filtro.
2. DBA confirmar mapeamento VALOR1–4.
3. Executar **7 dias** (Etapa B) após aceite do dia único.
4. Somente então **30 dias** fora do horário de pico.
