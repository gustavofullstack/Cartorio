# Roteiros LGPD-safe de Prospecção — Visão Geral

**Versão**: 1.0
**Data**: 23/06/2026
**Owner**: Rein `cartorio-lgpd`
**Quem usa**: Gustavo Almeida (prospecção manual)
**Base legal**: LGPD Lei 13.709/2018 + Provimento CNJ 74/2018
**DPO**: dpo@2notasudi.com.br

> Este pacote contém **11 modelos de copy** de prospecção B2B para cartórios, organizados em 3 canais (WhatsApp, e-mail, LinkedIn). Cada modelo passa no checklist de **5 critérios CEO** e cumpre os arts. 7º, 8º, 9º, 18 e 37 da LGPD.

---

## Estrutura

```
docs/leads/roteiros/
├── README.md                 ← este arquivo
├── whatsapp/
│   ├── 01-vampre-14sp.md              (personalizado, Tier A)
│   ├── 02-cartorio-amaral-5bh.md      (personalizado, Tier A — TOP 1)
│   ├── 03-cartorio-jaguarao-2bh.md    (personalizado, Tier A)
│   ├── 04-5tabelionato-londrina.md    (personalizado, Tier A)
│   └── 05-cartorio-herrera-1salvador.md (personalizado, Tier B)
├── email/
│   ├── 01-institucional-tier-a.md     (cold outreach, placeholders)
│   ├── 02-seguimento-7-dias.md        (follow-up 7d úteis)
│   └── 03-ultimo-follow-up.md         (encerramento de ciclo)
└── linkedin/
    ├── 01-conexao-tabeliao.md         (nota de conexão, ≤ 300 chars)
    ├── 02-mensagem-pos-aceite.md      (DM pós-aceite)
    └── 03-comentario-post.md          (estratégia conteúdo-first)
```

**Total**: 11 arquivos.

---

## Checklist CEO — 5 critérios obrigatórios

Todas as 11 copies passaram nos 5 critérios (verificado arquivo por arquivo):

### 1. Sinal específico por cartório (anti-spam)
- **5 WhatsApp personalizados** com 1 sinal concreto e verificável por cartório
  - Vampre: ">R$ 90M/ano ANOREG 2025"
  - Amaral: "2 números WhatsApp Business + LinkedIn ativo"
  - Jaguarao: "5º lugar GPTW MG 2026"
  - Londrina: "novo endereço 2025 (Av. Maringá, 201)"
  - Herrera: "único BA no top 30 nacional"
- **6 templates com placeholders** `{{SINAL_ESPECIFICO}}` para preenchimento manual

### 2. LGPD-safe (compliance)
- **Zero dado pessoal** (CPF, RG, nome do tabelião PF, telefone pessoal, e-mail pessoal)
- **Apenas dado institucional** (nome do cartório, cargo público, site, WhatsApp Business, e-mail institucional)
- **Sem pressão abusiva**: zero "última chance", "só hoje", "vagas limitadas"
- **Opt-out claro em todas** (rodapé): "Se preferir não receber esse tipo de mensagem, é só me avisar que paro. Mensagem em conformidade com LGPD."
- **Sem link rastreável** pessoal
- **Link institucional** do produto (link do piloto no site)

### 3. CTA claro (conversão)
- **NÃO** usa: "Vamos marcar?", "Topa uma conversa?", "Quer saber mais?"
- **SIM** usa: "Posso mostrar 15min terça 30/06 às 10h ou quinta 02/07 às 14h?"
- **Tempo curto**: 15min (não 1h)
- **2 opções concretas** (não 3+)
- **Dia útil + horário comercial** (8h-18h)
- **Pré-compromisso leve** ("conversa rápida", não "reunião de demonstração")

### 4. Tom PT-BR natural (anti-juridiquês)
- **Bloqueios lexicais** verificados em todos os 11 arquivos (zero ocorrências):
  - "Vossa Senhoria"
  - "venho por meio desta"
  - "solicito"
  - "informamos que"
  - "coloco-me à disposição"
  - "aguardo retorno"
  - "atenciosamente"
- **Boas práticas aplicadas**:
  - "tu/você" (não "Vossa Senhoria")
  - Parágrafos curtos (max 3 linhas)
  - 1 ideia por parágrafo
  - Frases de abertura curtas ("Vi que...", "Parabéns pelo...", "Notei que...")
  - Tom profissional mas direto, sem ser robótico

### 5. Piloto 30 dias (prova social)
- **WhatsApp e e-mail**: 1 linha com proposta concreta
  - "Ofereço 30 dias grátis em troca de depoimento + logomarca no case. Sem custo, sem compromisso."
- **LinkedIn (nota de conexão)**: NÃO mencionado (limite 300 chars); será mencionado na DM pós-aceite
- **LinkedIn (comentário)**: NÃO mencionado (canal não é de venda; é de conteúdo)

---

## Limites operacionais por canal

| Item | WhatsApp pessoal | E-mail | LinkedIn |
|------|------------------|--------|----------|
| Mensagens por dia | máx. 20 | máx. 10 | máx. 5 (DM) / máx. 5 (comentários) |
| Follow-ups por destinatário | 0 (cold) | máx. 2 (7d + 14d) | 0 (conexão) / 1 (DM) |
| Horário de envio | 09h–18h BRT (seg-sex) | 09h–18h BRT (seg-sex) | 09h–18h BRT (seg-sex) |
| Tempo de espera por resposta | 5 dias úteis | 7 dias úteis | 14 dias (conexão) / 7 dias (DM) |
| Tentativas após opt-out | 0 | 0 | 0 |

---

## Como usar este pacote

### Passo 1 — Escolher o canal primário por cartório

| Sinal do cartório | Canal primário sugerido |
|-------------------|--------------------------|
| WhatsApp Business ativo | **WhatsApp** (ver whatsapp/01-05) |
| Sem WhatsApp / e-mail institucional óbvio | **E-mail** (ver email/01-03) |
| Tabelião ativo no LinkedIn com posts recentes | **LinkedIn comentário** (ver linkedin/03) → DM (linkedin/02) |
| Tabelião inerte / conservador | **E-mail** (mais formal, sem pressão) |

### Passo 2 — Preencher placeholders (para os 6 templates genéricos)

Cada template lista 5 placeholders no topo:

```
{{NOME_CARTORIO}}      ← público, do site oficial
{{SINAL_ESPECIFICO}}   ← 1 sinal concreto e verificável
{{NOME_TABELIAO}}      ← (opcional, só se público)
{{CANAL_CONTATO}}      ← e-mail ou telefone institucional
{{CTA_HORARIO}}        ← 2 opções concretas (ter/qua/qui, 10h/14h)
```

**Fontes válidas para preenchimento**:
- Site oficial do cartório
- Ranking ANOREG/BR (https://www.anoreg.org.br)
- Google Maps / Google Meu Negócio
- LinkedIn institucional
- Matérias Migalhas / Conjur / JusBrasil
- Cadastro Nacional de Serventias (CNS) do CNJ

**Fontes proibidas**:
- Listas compradas
- Facebook Leads
- Scraping não autorizado
- Dados pessoais sem consentimento anterior

### Passo 3 — Rodar checklist pré-envio (de cada arquivo)

```
[ ] Sinal específico é verificável e público?
[ ] Zero dado pessoal (CPF, RG, nome PF, tel pessoal, email pessoal)?
[ ] Opt-out claro na última linha?
[ ] CTA com 15min + 2 opções concretas + dia útil + horário comercial?
[ ] Zero bloqueio lexical (juridiquês)?
[ ] Piloto 30d mencionado (WhatsApp/e-mail/DM, não comentário)?
[ ] Hoje ainda não enviei mais que o limite diário do canal?
[ ] Este número NÃO está marcado como opt_out no CRM?
```

Se qualquer resposta for **NÃO**, **não envie**.

### Passo 4 — Registrar no CRM

Cada interação deve ser registrada em planilha/CRM com:

| Campo | Descrição |
|-------|-----------|
| `data_envio_msg1` | ISO 8601 |
| `nome_tabeliao` | Público, do CNS/site |
| `nome_cartorio` | Público |
| `canal` | whatsapp / email / linkedin |
| `telefone_ou_email` | Público |
| `fonte` | URL do site ou CNS |
| `sinal_usado` | 1 linha do sinal específico |
| `consentimento` | true / false / null |
| `data_consentimento` | ISO 8601 |
| `opt_out` | true / false / null |
| `data_opt_out` | ISO 8601 |
| `status_final` | convertido / opt_out / sem_resposta / em_conversa |

**Retenção deste registro**: 5 anos (LGPD art. 37 — log de operação comercial).

---

## Top 5 prioritários (personalizados, prontos pra envio)

| # | Cartório | Canal | Arquivo |
|---|----------|-------|---------|
| 1 | 5º Ofício de Notas de BH (Cartório Amaral) | WhatsApp | `whatsapp/02-cartorio-amaral-5bh.md` |
| 2 | 14º Tabelião SP (Vampre) | WhatsApp | `whatsapp/01-vampre-14sp.md` |
| 3 | 2º Tabelionato BH (Cartório Jaguarao) | E-mail | `email/01-institucional-tier-a.md` + `whatsapp/03-cartorio-jaguarao-2bh.md` |
| 4 | 5º Tabelionato Londrina | WhatsApp | `whatsapp/04-5tabelionato-londrina.md` |
| 5 | 1º Tabelionato Salvador (Cartório Herrera) | WhatsApp | `whatsapp/05-cartorio-herrera-1salvador.md` |

---

## Revisão pós-uso

A cada **30 dias**, revisar:

1. **Qual canal converteu mais?** (whatsapp / email / linkedin)
2. **Qual sinal específico gerou mais respostas?**
3. **Qual horário/dia teve melhor taxa de resposta?**
4. **Quantos opt-outs?** (esperado: < 5% dos contatados)
5. **Quantas conversões?** (meta: 2-3 demos agendadas por mês)

Salvar lições em `.harness/memory/MEMORY.md`.

---

## O que é proibido

- ❌ Envio em massa (Meta bane + ANPD multa)
- ❌ Usar dado pessoal não-público
- ❌ Pressão abusiva (urgência artificial, escassez falsa)
- ❌ Insistir após opt-out ou "não tenho interesse" (LGPD art. 18 IX)
- ❌ Comprar listas de leads (LGPD art. 6º VIII — prevenção)
- ❌ Compartilhar a base de opt-out com terceiros
- ❌ Link rastreável (utm pessoal, bit.ly com nome destinatário)
- ❌ Bloqueios lexicais (juridiquês)

---

## Resposta a reclamação (playbook)

Se o destinatário reclamar formalmente (ANPD, Procon, jurídico):

1. **Confirmar recebimento** em até 24h
2. **Remover contato** da base imediatamente
3. **Investigar** o que causou a reclamação (origem do dado? opt-out ignorado?)
4. **Responder formalmente** em até 15 dias úteis (LGPD art. 18 §5º)
5. **Documentar** em `.harness/memory/MEMORY.md` como lição
6. **Se houver risco ≥ médio**: notificar DPO em até 24h e ANPD em até 72h (LGPD art. 48)

---

## Versionamento

| Versão | Data | Mudança | Aprovado por |
|--------|------|---------|--------------|
| 1.0 | 23/06/2026 | Pacote inicial (11 copies, 3 canais, 5 critérios) | DPO + cartorio-lgpd |

---

**Modified by Gustavo Almeida**