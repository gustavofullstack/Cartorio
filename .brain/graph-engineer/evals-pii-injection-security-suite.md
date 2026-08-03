# Suíte PII, Prompt Injection e Data Exfiltration · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.43  
**Status:** APROVADO (SPARK + PRO Review)

## Evidência de Suíte de Segurança

- **Prompt Injection Tests:** Injeções do tipo "ignore previous instructions", "print your system prompt", "tell me internal keys" bloqueadas.
- **PII Leak Tests:** Tentativas de extração de CPF/RG de terceiros mascaradas via `pii_sanitizer.py`.

