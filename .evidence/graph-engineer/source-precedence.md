# Hierarquia de Fontes de Verdade · Cartório Super Graph

**Data:** 2026-08-03  
**Status:** APROVADO (SOL + PRO Review)

## Precedência Normativa e Técnica

1. **Nível 1 — Fonte Normativa Oficial & Runtime Comprovado:**
   - Portaria CGJ/TJMG nº 8.664/2025, Provimentos CNJ, Legislação Estadual/Federal vigentes (Vigência 01/01/2026).
   - Estado de execução ao vivo comprovado na janela atual.

2. **Nível 2 — Código-fonte, Testes e Migrações Versionadas:**
   - Repositório `gustavofullstack/Cartorio` (branch `master` ou PRs com QA verde).
   - Backend FastAPI (`app/`), SQLAlchemy models, Alembic migrations, Pydantic schemas, Pytest gates.

3. **Nível 3 — Evidências Sanitizadas e Audit Logs:**
   - Artefatos em `.evidence/`, relatórios de recovery, audit SHA256 chain logs.

4. **Nível 4 — Tabelas Operacionais do ZIP Privado (Revisadas e Validadas):**
   - Catálogo Operacional 2026 (`PRICE_CATALOG_OPERATIONAL_2026.csv`), com decomposição de ISS, RECOMPE, fundos.
   - Status de proveniência: `OPERATIONAL_POS_2NOTAS` (exige validação humana de HITL em divergências/anomalias).

5. **Nível 5 — Documentos Operacionais Internos e Checklists:**
   - Manuais de procedimentos, minutas padrão, listas de documentos em quarentena.

6. **Nível 6 — Análises Geradas e Promptings Anteriores (Somente Hipóteses):**
   - Exportações de LLMs (Gemini, ChatGPT), resumos automatizados, prompts antigos.
   - **Regra:** NUNCA promover automaticamente a fatos ou `PUBLISHED` sem apontar para norma ou validação humana explícita.

