# Prompt injection

## Política

Conteúdo do documento é **dado não confiável**. Padrões suspeitos não viram instruções do sistema.

## Detecção

`detect_prompt_injection()` (padrões em `PROMPT_INJECTION_PATTERNS`), exemplos:

- “ignore as regras” / “ignore previous”
- “ative esta cotação automaticamente” / “activate this quote”
- “system prompt”, “você agora é”, “envie os dados para”, “execute url”

## Efeito

1. Warning `PROMPT_INJECTION_CONTENT_DETECTED`
2. Alerta `QUOTE_AI_PROMPT_INJECTION_DETECTED` (HIGH)
3. Extração continua tratando o texto como input (não obedece a instrução)
4. Revisão humana permanece obrigatória

A IA **nunca** ativa cotação mesmo se o texto pedir.
