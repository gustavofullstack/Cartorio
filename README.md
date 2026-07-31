# Projeto Cartório - Pipeline BRAIN (15 Etapas Concluídas)

Sistema completo para inventário documental, interpretação jurídica notarial, classificação, validação, cálculo de emolumentos/impostos, cálculo sucessório, e-Notariado, fluxos extrajudiciais, integração com o Lark (Feishu), recepção de arquivos ZIP sem perdas, gerenciador de memória de conversas multi-turn e rastreabilidade por agente.

## 🚀 Estrutura de Diretórios

```
/Users/gustavoalmeida/Cartorio/
├── documents/                # 90 documentos extraídos (.docx, .pdf, .odt, .txt)
├── inventory.json            # Inventário estruturado com texto integral (385.070 palavras)
├── legal_rules.json          # Regras jurídicas, checklists, emolumentos e provimentos
├── brain.db                  # Banco SQLite de produção local
├── ARCHITECTURE.md           # Documentação arquitetural completa (15 Etapas)
├── README.md                 # Guia do usuário e da CLI
├── brain/                    # Pacote Python BRAIN
│   ├── db.py                 # Banco de dados e indexação
│   ├── document_identifier.py# Identificação e classificação documental
│   ├── calculations.py       # Emolumentos e comparação ITCMD vs ITBI
│   ├── validations.py        # Validação de requisitos e cláusulas
│   ├── knowledge_base.py     # Motor de busca legal e provimentos
│   ├── felipe_templates.py   # Modelos e padrões do Tabelião Substituto Felipe Pizarro
│   ├── drafting_engine.py    # Gerador dinâmico de minutas e e-mails de exigência
│   ├── jurisprudence_matrix.py# Matriz de jurisprudência STJ e provimentos CNJ
│   ├── enotariado_engine.py  # Competência territorial e e-Notariado
│   ├── usucapiao_adjudicacao_workflow.py # Fluxos extrajudiciais (Usucapião / Adjudicação)
│   ├── estremacao_engine.py  # Validador de Estremação e Condomínio
│   ├── succession_engine.py  # Calculadora de meação, herança e justa causa
│   ├── lark_zip_handler.py   # Ingestão resiliente de arquivos ZIP do Lark
│   ├── conversation_memory.py# Memória de conversas multi-turn e estado de sessão
│   ├── execution_promise_engine.py # Motor de execução de promessas sem stalling
│   ├── lark_agent_protocol.py# Bridge de integração com Webhooks do Lark
│   ├── privacy_sanitizer.py  # Proteção e mascaramento de PII
│   ├── traceability.py       # Log de auditoria por agente
│   └── brain_cli.py          # Interface de Linha de Comando (CLI)
└── tests/                    # Suíte de testes automatizados com Pytest (35 testes)
```

## 🛠️ Guia de Uso da CLI BRAIN

### 1. Ingestão de Arquivo ZIP do Lark (Sem perda de arquivos)
```bash
python3 -m brain.brain_cli receive-zip --file /Users/gustavoalmeida/Downloads/Cartorio-20260731T144042Z-1-001.zip
```

### 2. Simular Mensagem do Lark com Retenção de Memória
```bash
python3 -m brain.brain_cli lark-msg --session "lark_sess_100" --sender "Gustavo" --text "Te mandei esse zip..." --zip "/Users/gustavoalmeida/Downloads/Cartorio-20260731T144042Z-1-001.zip"
```

### 3. Consultar Histórico de Memória da Conversa
```bash
python3 -m brain.brain_cli memory --session "lark_sess_100"
```

### 4. Calcular Quotas Sucessórias e Meação
```bash
python3 -m brain.brain_cli succession --value 1500000 --regime "Comunhão Parcial de Bens" --children 3
```

### 5. Verificar Competência Territorial no e-Notariado
```bash
python3 -m brain.brain_cli enotariado --property "Uberlândia" --domicile "Uberlândia"
```

### 6. Redigir Minuta de Testamento Público com Diligência (Padrão Felipe Pizarro)
```bash
python3 -m brain.brain_cli draft --testador "Dr. Roberto" --medico "Dra. Juliana"
```

### 7. Gerar Resposta Oficial de Exigência Notarial para Matrículas
```bash
python3 -m brain.brain_cli email-response
```

### 8. Consultar Matriz de Jurisprudência STJ / CNJ
```bash
python3 -m brain.brain_cli precedent --q "Nancy Andrighi"
```

### 9. Calcular Emolumentos e Comparativo Tributário (ITCMD vs ITBI)
```bash
python3 -m brain.brain_cli calculate --value 500000 --act Escritura
```

### 10. Validar Requisitos de Documentação
```bash
python3 -m brain.brain_cli validate --act "Inventário e Partilha" --docs "Certidão de Óbito, RG e CPF das Partes, Certidão de Casamento"
```

## 🧪 Execução da Suíte de Testes (Pytest)

Para rodar os 35 testes automatizados com validação de 100% dos componentes:

```bash
python3 -m pytest /Users/gustavoalmeida/Cartorio/tests -v
```

## 🔒 Segurança e Privacidade
- Todos os dados sensíveis (CPFs, RGs, e-mails, telefones) são sanitizados via `PrivacySanitizer`.
- O runtime Hermes em produção (`/Users/gustavoalmeida/.hermes`) permaneceu 100% intacto e sem alterações.
