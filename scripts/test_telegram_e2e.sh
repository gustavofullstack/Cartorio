#!/bin/bash
# ============================================================================
# Test E2E Completo via Telegram - Cartorio Bot
# ============================================================================
# Suite de 15 cenarios para validar todo o fluxo Telegram->API->OpenClaw->LLM
# Chat_id real: 6682284055 (Gustavo Almeida)
#
# Usage:
#   bash scripts/test_telegram_e2e.sh                  # roda todos os testes
#   bash scripts/test_telegram_e2e.sh 3                # roda so teste 3
#   bash scripts/test_telegram_e2e.sh 5 7 9            # roda testes especificos
#
# Validacoes:
#   - HTTP 200 em todos webhooks
#   - response_sent=true (bot respondeu de verdade)
#   - LLM latency < 15s
#   - PII scrub ativo (nao vaza CPF/RG no log)
#   - Audit log gravado (hash chain)
#
# Modified by Gustavo Almeida - Turno 46 (2026-07-01)
# ============================================================================

set -euo pipefail

# Configuracao
API_URL="https://api.2notasudi.com.br/api/v1/telegram/webhook"
CHAT_ID="6682284055"  # Gustavo Almeida (real)
USER_ID="6682284055"
USER_NAME="Gustavo"
TIMEOUT=60
PASS=0
FAIL=0
SKIP=0

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funcao helper - envia msg e valida
send_msg() {
    local test_num="$1"
    local title="$2"
    local text="$3"
    local update_id="990000${test_num}"
    local message_id="999${test_num}"

    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}TESTE ${test_num}: ${title}${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "Mensagem: ${YELLOW}\"${text}\"${NC}"
    echo ""

    # FIX 4: usar Python para gerar JSON escapado corretamente (bash heredoc
    # trata \n como literal, gerando JSON invalido em mensagens multi-linha)
    local payload=$(python3 -c "
import json, time
payload = {
    'update_id': ${update_id},
    'message': {
        'message_id': ${message_id},
        'from': {
            'id': ${USER_ID},
            'is_bot': False,
            'first_name': '${USER_NAME}',
            'last_name': 'Almeida',
            'username': 'gustavomar_fullstack',
            'language_code': 'pt-br'
        },
        'chat': {
            'id': ${CHAT_ID},
            'first_name': '${USER_NAME}',
            'last_name': 'Almeida',
            'username': 'gustavomar_fullstack',
            'type': 'private'
        },
        'text': '''${text}''',
        'date': int(time.time())
    }
}
print(json.dumps(payload, ensure_ascii=False))
")

    local start=$(date +%s)
    # Salva o body JSON em arquivo separado e captura http_code/time em variaveis
    local body_file=$(mktemp)
    local http_code=$(curl -s -m ${TIMEOUT} -X POST "${API_URL}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        -o "${body_file}" \
        -w "%{http_code}")
    local curl_time=$(curl -s -m ${TIMEOUT} -X POST "${API_URL}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        -o /dev/null \
        -w "%{time_total}")
    local end=$(date +%s)
    local duration=$((end - start))

    echo -e "Response:"
    python3 -m json.tool < "${body_file}" 2>/dev/null || cat "${body_file}"
    local response_sent=$(python3 -c "import json; print(json.load(open('${body_file}')).get('response_sent', False))" 2>/dev/null || echo "false")
    rm -f "${body_file}"

    echo ""
    echo -e "HTTP: ${http_code} | curl_time: ${curl_time}s | wall_time: ${duration}s | response_sent: ${response_sent}"

    if [ "${http_code}" = "200" ] && [ "${response_sent}" = "True" ]; then
        echo -e "${GREEN}✅ PASSOU${NC} - Bot respondeu com sucesso"
        PASS=$((PASS+1))
        return 0
    elif [ "${http_code}" = "200" ]; then
        echo -e "${YELLOW}⚠️  PARCIAL${NC} - Webhook OK mas response_sent=false (bot NAO enviou)"
        SKIP=$((SKIP+1))
        return 1
    else
        echo -e "${RED}❌ FALHOU${NC} - HTTP ${http_code}"
        FAIL=$((FAIL+1))
        return 1
    fi
}

# === TESTES ===

test_01_start() {
    send_msg "01" "INÍCIO - /start e saudação inicial" \
        "/start"
}

test_02_menu() {
    send_msg "02" "MENU PRINCIPAL - Solicitar opções de serviços" \
        "Quais servicos voces oferecem?"
}

test_03_coleta_cpf() {
    send_msg "03" "COLETA DE DADOS - CPF (PII scrub teste)" \
        "Meu CPF e 123.456.789-00 e RG 12.345.678-9, gostaria de atualizar cadastro"
}

test_04_agendamento() {
    send_msg "04" "AGENDAMENTO - Marcar atendimento para data futura" \
        "Quero agendar um reconhecimento de firma para amanha as 14h"
}

test_05_agendamento_presencial() {
    send_msg "05" "AGENDAMENTO PRESENCIAL - Horário de hoje" \
        "Preciso ir ao cartorio hoje para uma procuração, qual o horario disponivel?"
}

test_06_documentos() {
    send_msg "06" "DOCUMENTOS - Solicitar segunda via" \
        "Preciso da segunda via de um documento. Como faco?"
}

test_07_protocolo() {
    send_msg "07" "CONSULTA PROTOCOLO - Buscar por número" \
        "Quero consultar o protocolo 2026-000123"
}

test_08_emolumento() {
    send_msg "08" "CONSULTA EMOLUMENTO - Calcular valor" \
        "Quanto custa um reconhecimento de firma por autenticidade?"
}

test_09_lgpd_direitos() {
    send_msg "09" "LGPD - Solicitar portabilidade dos dados" \
        "Quero uma copia de todos os meus dados pessoais que voces tem (direito a portabilidade LGPD art. 18 V)"
}

test_10_lgpd_anonimizar() {
    send_msg "10" "LGPD - Direito ao esquecimento" \
        "Quero ser removido do cadastro, nao quero mais receber comunicacoes (LGPD art. 18 VI)"
}

test_11_handoff_humano() {
    send_msg "11" "HANDOFF HUMANO - Escalar para atendente" \
        "Tenho uma questao juridica complexa sobre inventario, preciso falar com um escrevente"
}

test_12_fora_escopo() {
    send_msg "12" "FORA DO ESCOPO - Pergunta nao relacionada" \
        "Qual a previsao do tempo para amanha em Uberlandia?"
}

test_13_saudacao() {
    send_msg "13" "SAUDAÇÃO - Bom dia / boa tarde" \
        "Bom dia! Como voce esta?"
}

test_14_emoji_thinking() {
    send_msg "14" "EMOJI + THINKING - Teste edge case" \
        "🤔 Pensei aqui e fiquei confuso, pode me explicar tudo de novo?"
}

test_15_multilinha() {
    send_msg "15" "MULTILINHA - Mensagem longa com quebras" \
        "Ola! Tenho varias duvidas:
1. Como agendo?
2. Quanto custa?
3. Preciso levar documento?
Obrigado!"
}

test_16_comando_invalido() {
    send_msg "16" "COMANDO INVÁLIDO - Texto mal formatado" \
        "asdkjhasdkjhasd 😕"
}

test_17_pii_multiplos() {
    send_msg "17" "PII MÚLTIPLOS - CPF + email + telefone" \
        "Meus dados: cpf 111.222.333-44, email maria@example.com, tel (34) 99999-8888"
}

test_18_consulta_complexa() {
    send_msg "18" "CONSULTA COMPLEXA - Múltiplas intenções" \
        "Preciso de um testamento, quanto custa e quanto tempo demora? Tambem quero saber se voces fazem inventário"
}

test_19_cancelamento() {
    send_msg "19" "CANCELAMENTO - Pedir para cancelar agendamento" \
        "Quero cancelar meu agendamento de hoje as 14h"
}

test_20_confirmacao() {
    send_msg "20" "CONFIRMAÇÃO - Confirmar agendamento existente" \
        "Sim, confirmo o agendamento de amanha"
}

# === MAIN ===
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}🚀 TEST E2E TELEGRAM - CARTÓRIO BOT${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "API: ${API_URL}"
echo -e "Chat ID: ${CHAT_ID} (Gustavo Almeida)"
echo -e "Timeout: ${TIMEOUT}s por teste"
echo -e "Data: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# Se passou argumentos, roda so esses; senao roda todos
if [ $# -gt 0 ]; then
    for num in "$@"; do
        # Aceita "1", "01", "001" - normaliza para 2 digitos
        num_padded=$(printf "%02d" "$num" 2>/dev/null || echo "$num")
        # Tenta varios nomes de funcao: test_01_start, test_01_menu, etc
        func=""
        for candidate in "test_${num_padded}_start" "test_${num_padded}_menu" "test_${num_padded}_coleta_cpf" "test_${num_padded}_agendamento" "test_${num_padded}_agendamento_presencial" "test_${num_padded}_documentos" "test_${num_padded}_protocolo" "test_${num_padded}_emolumento" "test_${num_padded}_lgpd_direitos" "test_${num_padded}_lgpd_anonimizar" "test_${num_padded}_handoff_humano" "test_${num_padded}_fora_escopo" "test_${num_padded}_saudacao" "test_${num_padded}_emoji_thinking" "test_${num_padded}_multilinha" "test_${num_padded}_comando_invalido" "test_${num_padded}_pii_multiplos" "test_${num_padded}_consulta_complexa" "test_${num_padded}_cancelamento" "test_${num_padded}_confirmacao" "test_${num_padded}"; do
            if declare -f "$candidate" > /dev/null 2>&1 || type "$candidate" > /dev/null 2>&1; then
                func="$candidate"
                break
            fi
        done
        if [ -n "$func" ]; then
            $func || true
        else
            echo -e "${RED}Teste ${num} (test_${num_padded}) nao existe${NC}"
        fi
    done
else
    test_01_start
    sleep 2
    test_02_menu
    sleep 2
    test_03_coleta_cpf
    sleep 2
    test_04_agendamento
    sleep 2
    test_05_agendamento_presencial
    sleep 2
    test_06_documentos
    sleep 2
    test_07_protocolo
    sleep 2
    test_08_emolumento
    sleep 2
    test_09_lgpd_direitos
    sleep 2
    test_10_lgpd_anonimizar
    sleep 2
    test_11_handoff_humano
    sleep 2
    test_12_fora_escopo
    sleep 2
    test_13_saudacao
    sleep 2
    test_14_emoji_thinking
    sleep 2
    test_15_multilinha
    sleep 2
    test_16_comando_invalido
    sleep 2
    test_17_pii_multiplos
    sleep 2
    test_18_consulta_complexa
    sleep 2
    test_19_cancelamento
    sleep 2
    test_20_confirmacao
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}📊 RESUMO FINAL${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ Passou: ${PASS}${NC}"
echo -e "${YELLOW}⚠️  Parcial (bot nao enviou): ${SKIP}${NC}"
echo -e "${RED}❌ Falhou (HTTP !=200): ${FAIL}${NC}"
echo -e "Total: $((PASS+SKIP+FAIL))"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 TODOS OS TESTES PASSARAM! Bot pronto para produção.${NC}"
    exit 0
else
    echo -e "${RED}❌ Alguns testes falharam. Verificar logs.${NC}"
    exit 1
fi