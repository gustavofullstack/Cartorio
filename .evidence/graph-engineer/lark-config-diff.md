# Comparação de Configuração Versionada vs Carregada (Lark) · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.09  
**Status:** APROVADO (LUNA + PRO Review)

## Evidência de Configuração

- **Configuração Versionada:** `infra/hermes/lark-gateway.yaml` / `.env.example`.
- **Verificação Fail-Closed:** Secrets injetados estritamente via Docker Secrets / LaunchAgent environment; zero fallbacks com chaves literais no código ou repositório.

