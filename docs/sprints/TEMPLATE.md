# Sprint N — [Nome da sprint]

> **PDR** = Documento de Requisitos do Produto  
> **RDC** = Regras de Domínio e Critérios  
>
> Copie este arquivo para `sprint-NN.md` e preencha todas as seções antes de iniciar a implementação.

---

## 1. Identificação da sprint

| Item | Definição |
|------|-----------|
| Projeto | Inteligência Auto Postos |
| Sprint | Sprint N |
| Nome | [Nome] |
| Tipo | [Estrutural / Funcional / Integração / Analytics] |
| Duração sugerida | [X dias úteis] |
| Prioridade | [Crítica / Alta / Média] |
| Dependência | [Sprint anterior ou integração externa] |
| Resultado esperado | [Uma frase mensurável] |

---

## 2. PDR — Documento de Requisitos do Produto

### 2.1 Contexto

[Por que esta sprint existe no momento do roadmap]

### 2.2 Problema

[O que não funciona ou o que falta sem esta entrega]

### 2.3 Objetivo da sprint

[Lista objetiva do que será construído]

### 2.4 Objetivos de negócio

[Valor para compradores, gestores, financeiro, etc.]

### 2.5 Métricas de sucesso

| Métrica | Meta |
|---------|------|
| [Ex.: critérios de aceite atendidos] | 100% |
| [Ex.: cobertura de testes em regras críticas] | [X%] |

### 2.6 Premissas

- [Premissa 1]
- [Premissa 2]

---

## 3. Escopo

### 3.1 Dentro do escopo

**Backend**

- [ ]

**Frontend**

- [ ]

**Infraestrutura / integração**

- [ ]

**Qualidade e documentação**

- [ ]

### 3.2 Fora do escopo

- [ ]

---

## 4. Personas e permissões

| Persona | Necessidade nesta sprint | Permissões |
|---------|--------------------------|------------|
| ADMIN | | |
| GESTOR | | |
| COMPRADOR | | |
| FINANCEIRO | | |
| CONSULTA | | |

---

## 5. RDC — Regras de domínio e critérios

| ID | Regra |
|----|-------|
| RDC-NNN-001 | [Descrição clara e testável] |
| RDC-NNN-002 | |

---

## 6. Requisitos funcionais

| ID | Requisito |
|----|-----------|
| RF-001 | |
| RF-002 | |

---

## 7. Requisitos não funcionais

| ID | Requisito |
|----|-----------|
| RNF-001 | |
| RNF-002 | |

---

## 8. Casos de uso

### UC-001 — [Título]

**Ator:**  
**Pré-condições:**  
**Fluxo principal:**  
**Fluxos alternativos:**  
**Pós-condições:**  

---

## 9. Fluxos de UX

### 9.1 Objetivo da interface

### 9.2 Wireframes / telas

```text
[ASCII ou link para protótipo]
```

### 9.3 Estados visuais

| Estado | Comportamento |
|--------|---------------|
| Carregando | |
| Sucesso | |
| Erro | |
| Vazio | |

### 9.4 Regras de UX

- [ ]

---

## 10. Arquitetura e decisões técnicas

### 10.1 Diagrama

```text
[Diagrama de componentes ou sequência]
```

### 10.2 Decisões novas

Registrar em [technical-decisions.md](../architecture/technical-decisions.md) se houver ADR novo.

### 10.3 Impacto em módulos existentes

| Módulo | Alteração |
|--------|-----------|
| | |

---

## 11. Variáveis de ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| | | |

Atualizar `.env.example` se necessário.

---

## 12. Modelo de dados

### 12.1 Entidades novas

```text
[tabela]
- campo tipo constraints
```

### 12.2 Entidades alteradas

### 12.3 Migrations

- `NNNN_descricao.py`

### 12.4 Seeds

- [ ]

---

## 13. Contratos de API

### `[MÉTODO] /api/v1/...`

**Request**

```json
{}
```

**Response 200**

```json
{}
```

**Erros**

| HTTP | Código | Quando |
|------|--------|--------|
| 400 | | |
| 401 | | |
| 403 | | |
| 404 | | |

---

## 14. Tratamento de erros

- Códigos de erro de domínio: `[LISTA]`
- Mensagens ao usuário vs logs internos

---

## 15. Critérios de aceite

| ID | Critério | Status |
|----|----------|--------|
| CA-001 | | ⬜ |
| CA-002 | | ⬜ |

---

## 16. Plano de testes

### Backend (unitário / integração)

| # | Cenário | Tipo |
|---|---------|------|
| T1 | | pytest |

### Frontend

| # | Cenário | Tipo |
|---|---------|------|
| T1 | | manual / e2e |

### Regressão

- [ ] Health checks Sprint 0
- [ ] [Funcionalidade sprint anterior]

---

## 17. Definition of Ready

- [ ] PDR e RDC revisados
- [ ] Dependências da sprint anterior entregues
- [ ] Contratos de API esboçados
- [ ] Modelo de dados validado
- [ ] Critérios de aceite acordados

---

## 18. Definition of Done

- [ ] Todos os critérios de aceite ✅
- [ ] Migrations aplicadas e documentadas
- [ ] Testes passando
- [ ] Build frontend OK
- [ ] `docker compose up` funcional
- [ ] Documentação atualizada
- [ ] Sem segredos no Git
- [ ] Relatório final da sprint
- [ ] Próxima sprint não antecipada

---

## 19. Entregáveis

| Entregável | Caminho |
|------------|---------|
| | |

---

## 20. Tarefas técnicas sugeridas

### Backend

- [ ]

### Frontend

- [ ]

### Documentação

- [ ]

---

## 21. Riscos e dependências

| Risco | Impacto | Tratamento |
|-------|---------|------------|
| | | |

**Dependências:** Sprint N-1, time XPERT, credenciais, etc.

---

## 22. Status de implementação

_Preencher após a execução._

### Concluído

-

### Débito técnico / gaps

| Item | Esperado | Atual |
|------|----------|-------|
| | | |

---

## 23. Script completo para o Cursor IA

```text
PROJETO: INTELIGÊNCIA AUTO POSTOS
SPRINT: N
NOME: [NOME]

Atue como arquiteto e desenvolvedor full stack sênior.

Antes de alterar qualquer arquivo:
1. Inspecione a implementação das sprints anteriores.
2. Leia docs/sprints/sprint-NN.md (este documento).
3. Preserve padrões existentes.
4. Não implemente sprints futuras.

OBJETIVO
[Copiar seção 2.3]

REGRAS OBRIGATÓRIAS
[Copiar RDC e restrições]

ENTIDADES / API / UX
[Copiar seções 12, 13, 9]

CRITÉRIOS DE ACEITE
[Copiar seção 15]

TESTES
[Copiar seção 16]

DOCUMENTAÇÃO
Atualizar README, technical-decisions, docs/database se aplicável.

ENTREGA FINAL
1. Resumo funcional
2. Arquivos criados/alterados
3. Migrations
4. Testes e resultados
5. Build frontend
6. Comandos
7. Pendências e riscos
8. Confirmação de que sprint N+1 não foi antecipada

Não avance para a Sprint N+1.
```
