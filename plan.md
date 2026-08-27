## Tarefas Consolidadas - P0 e Incidentes (2026-07-28)

1. **Fix FB1: "isenção"/"urgência" offline fallback proativo**
   - Modificar `backend/app/services/cartorio_agent.py` na função `_detect_intent` para escalar requisições com "isenç", "urgente", "escritura", "certidão", "testamento", "inventário", "usucapião" para a `intent` `"humano"` (hitl_required=true). Atualmente, a string "isenção" cai em `intent:preco` e não escala no fluxo determinístico.
   - A intenção `humano` deve ter precedência antes da verificação de `intent:preco`.

2. **Fix FB5: Mascaramento (Scrubbing) de RG padrão MG**
   - Modificar `backend/app/services/pii.py` e atualizar a regex `"rg"` em `_PATTERNS`.
   - Formato atual: exige pontos e verificador (`r"\b\d{1,2}\.\d{3}\.?\d{3}-?[\dxX]\b"`).
   - Deve mascarar o formato de Minas Gerais (ex: `MG-12.345.678`, `12.345.678 SSP MG`, `123456789`).
   - A regex do RG deve abranger letras prefixadas opcionais (como UF), aceitar espaços opcionais, SSP, e dígitos flexíveis.
   - Ao mesmo tempo, não deve colidir com CEP (por isso deve continuar antes do CEP na lista do `_PATTERNS` e ser testada rigorosamente para não colidir).
   - Também atualizar testes (ou verificar) se os RGs sem pontos e verificadores são identificados corretamente se precedidos da keyword.

3. **Fix FB10: Canal iMessage suportado nos schemas do /lgpd/access**
   - Modificar `backend/app/api/v1/bot_lgpd.py` para incluir o canal `"imessage"`.
   - Atualizar todos os 4 schemas: `CancelarRequest`, `ExportRequest`, `AccessRequest` e qualquer outro modelo aplicável.
   - Substituir `channel: Literal["telegram", "whatsapp"]` por `channel: Literal["telegram", "whatsapp", "imessage"]`.

4. **Pre-commit Instructions**
   - Rodar testes, linters e formatadores.
