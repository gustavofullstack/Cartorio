# Plano de extracao de dados e fontes publicas

**Estado:** baseline tecnico para decisao. Nao autoriza coleta em producao.

## 1. Base instalada observada

O Postgres/Supabase da VPS e compartilhado por quatro dominios. A extracao
deve sempre comecar por API ou consulta de leitura; nunca por raspagem de
telas administrativas.

| Dominio | Tabelas/familias observadas | Uso analitico permitido |
|---|---|---|
| Core cartorial | `clientes`, `protocolos`, `documentos`, `agendamentos`, `atendimentos`, `conversas`, `sessoes` | Apenas agregados, pseudonimos e visoes aprovadas pelo DPO |
| Conformidade | `audit_log`, `lgpd_consent_log`, `lgpd_audit_anpd`, `cnj_export_requests` | Auditoria e indicadores; sem reidentificacao |
| Operacao de canais | `webhook_events`, `outbox_messages`, `fonte_capturas` | SLA, falhas, volume e qualidade de captura |
| Emolumentos | `emolumento_itens`, `fonte_capturas` | Catalogo versionado, origem, vigencia e comparacao humana |
| Chatwoot | `accounts`, `contacts`, `conversations`, `messages`, `inboxes`, `agent_bots` | Metricas por canal e fila, via API oficial do CRM |
| n8n | `workflow_entity`, `execution_entity`, `credentials_entity` e correlatas | Inventario e telemetria por API; credenciais jamais entram em extracoes |

O inventario LGPD do projeto identifica campos de identificacao, contato,
hashes e navegacao. Nome, e-mail, identificadores e conteudo de conversa nao
podem entrar em datasets de IA ou scraping.

## 2. Arquitetura segura de coleta

```text
Fonte publica/API oficial -> coletor versionado -> zona bruta isolada
  -> validacao (schema, origem, data, hash) -> normalizacao
  -> catalogo de fontes / dashboard agregado -> revisao humana
```

Regras para todo coletor:

1. Preferir API, arquivo oficial ou feed a HTML scraping.
2. Respeitar termos de uso, `robots.txt`, limites de requisicao e autoria.
3. Registrar URL, data de coleta, versao, hash do artefato e licenca em
   `fonte_capturas`; nao registrar dados pessoais desnecessarios.
4. Usar cache, backoff, idempotencia e fila. Nao fazer crawling sem limite de
   paginas, dominio e horario.
5. Transformar em indicadores agregados antes de expor ao agente de IA.
6. Toda mudanca de tabela oficial, valor ou interpretacao juridica permanece
   `DRAFT` ate validacao do escrevente/HITL.

## 3. Backlog de fontes externas

| Prioridade | Fonte e metodo | Produto de dados | Guardrail |
|---|---|---|---|
| P0 | Tabelas oficiais de emolumentos MG: download/API oficial quando disponivel; HTML somente se permitido | itens, vigencia, ato, faixa e referencia da fonte | dupla revisao humana antes de publicar/calcular |
| P0 | Datajud/CNJ: API publica, nao crawler de processos | metadados e tendencias publicas | cumprir Termo de Uso e excluir qualquer tentativa de perfilamento pessoal |
| P1 | Portais oficiais de normas e provimentos | normas, versoes, vigencias e trechos de referencia | fonte primaria, hash e revisao juridica |
| P1 | Portal de transparencia e dados abertos estritamente pertinentes | estatisticas territoriais agregadas | somente conjuntos com licenca/termo claro |
| P2 | Sites institucionais de parceiros autorizados | agenda, catalogo e estado de integracao | contrato/autorizacao e credencial de menor privilegio |

Nao entram no backlog: CPF/CNPJ de terceiros, certidoes, imagens de documentos,
dados de conversas, bases de redes sociais ou consultas que contornem login,
captcha, limite tecnico ou termo de uso.

## 4. Painel inicial recomendado

O painel deve ter dados agregados e cinco abas:

- **Fontes:** ultima coleta, idade, status, hash, licenca/termo e responsavel.
- **Emolumentos:** vigencia, variacao entre fontes, itens pendentes de revisao.
- **Atendimento:** volume por canal, tempo de primeira resposta, fila e falhas.
- **Automacoes:** webhook recebido, outbox, execucao de workflow e DLQ.
- **Conformidade:** consentimento, pedidos LGPD, integridade da auditoria e
  exportacoes CNJ por status.

Nenhuma aba deve mostrar texto de conversa, documento, CPF, telefone, e-mail,
IP integral ou segredo.

## 5. Portas de aprovacao antes da primeira coleta

- Dono da fonte e finalidade documentados.
- Termos de uso/licenca e taxa maxima registrados.
- DPO aprova a classificacao de dados e a retencao.
- Coletor possui teste com fixture publica, rate limit e trilha de auditoria.
- Saida passa por PII scrubber antes de qualquer modelo externo.
- Dashboard consulta somente visoes agregadas/read-only.

## Referencias externas verificadas em 2026-07-27

- CNJ Datajud disponibiliza API publica de metadados processuais e vincula o
  uso aos seus termos: <https://www.cnj.jus.br/sistemas/datajud/api-publica/>.
- A ANPD ressalta que dados publicos nao sao de reutilizacao irrestrita e que
  a possibilidade de reidentificacao volta a caracterizar dado pessoal:
  <https://www.gov.br/funasa/pt-br/acesso-a-informacao/lei-geral-de-protecao-de-dados-pessoais-lgpd/tipos-de-dados-abordados-pela-lgpd>.

