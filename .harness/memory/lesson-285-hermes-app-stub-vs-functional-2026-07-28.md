# Lesson 285 — Hermes.app stub em /Applications causa crashes silenciosos

**Data:** 2026-07-28
**Severidade:** média (crash + crash loop + ruído no log)
**Squad:** sre / devops

## Contexto

Gustavo reportou "Hermes caiu". Análise:

1. `/Applications/Hermes.app` = **stub de instalador** (Hermes-Setup 11MB, sem Electron Framework)
2. Binário stub referencia `@rpath/Electron Framework.framework` em path antigo:
   `~/Projetos/super-servidor-agentico/iso-build/agentos-v2.0/payload/agentos/macbook-snapshot/configs/hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app/...`
3. Esse path **não existe mais** (deletado em algum momento)
4. Toda vez que Hermes stub é lançado → SIGABRT imediato, library not loaded
5. LaunchAgent `ai.hermes.gateway-cartorio` abre Hermes de path funcional `~/.hermes/hermes-agent/...` que **funciona**
6. Resultado: dois Hermes, um crasha, outro roda. Confusão pra debugar.

## Sintomas

- Crash reports diários em `~/Library/Logs/DiagnosticReports/Hermes-*.ips`
- `bug_type: 309`, `termination: Library not loaded: Electron Framework.framework`
- macOS mostra "Hermes crashed" notifications
- Usuário pensa que "Hermes caiu" mas na verdade o **funcional** está OK

## Root cause

Mistura de instalador stub + path de build antigo deixado em `/Applications/`.
Apps Electron auto-update trocam o bundle mas mantêm o stub antigo que referencia
path do build anterior.

## Fix aplicado (2026-07-28)

```bash
# Backup do stub
mv /Applications/Hermes.app ~/.hermes_backup/Hermes.app.stub-YYYYMMDD

# Symlink pro app funcional
ln -s ~/.hermes/hermes-agent/apps/desktop/release/mac-arm64/Hermes.app \
       /Applications/Hermes.app

# Limpar crash reports > 30 dias
find ~/Library/Logs/DiagnosticReports -name "Hermes-*.ips" -mtime +30 -delete
```

Validação:
- `test -d "/Applications/Hermes.app/Contents/Frameworks/Electron Framework.framework"` → ✓

## Lição generalizável

**Ao debugar "app caiu":**

1. Sempre verificar se o `app.app` em `/Applications/` é **app real** (tem Frameworks/) ou **stub** (só MacOS/ instalador)
2. Crash reports com `bug_type: 309` + `Library not loaded` = stub faltando framework
3. Comparar PID vs launchctl: se launchctl abriu de outro path, o app "funcional" pode estar em outro lugar

**Prevenção:**

- Quando desinstalar app Electron, **remover também o stub de /Applications/**
- Quando buildar Electron localmente, **não colocar em /Applications** (usar Applications/electron-forge-output/)
- Auditar `Contents/Frameworks/` antes de assumir que app está funcional

Modified by Gustavo Almeida · 2026-07-28