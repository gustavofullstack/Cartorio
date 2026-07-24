"""
chatwoot_sim.py — Simulação de atendimentos via Chatwoot Inbox API.

Roda DENTRO do container `cartorio_api` na VPS, usando a rede interna Docker
Swarm (cartorio_chatwoot:3000) + token CHATWOOT_API_KEY que já está nas envs.

Cria 1 inbox `whatsapp-sim` e 10 personas sintéticas (Faker-style determinístico).
Cada persona abre 1 conversa e troca mensagens cliente↔agente simulando
atendimento real pelo WhatsApp.

LGPD-by-design: PII sintético (CPF/RG/telefone gerados, NÃO reais), mascarado
na camada de input via pi_sintetico() antes de enviar pro Chatwoot (defesa em
profundidade). Audit log fica na API via POST /api/v1/atendimentos.

Uso:
    docker exec -i cartorio_api.XYZ /app/.venv/bin/python - < chatwoot_sim.py
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Config (env)
# ---------------------------------------------------------------------------
# Override pra URL interna Swarm (não depende de DNS externo / Cloudflare).
# Se CHATWOOT_BASE_URL_INTERNAL não estiver setada, usa a pública.
BASE = os.environ.get("CHATWOOT_BASE_URL_INTERNAL") or os.environ["CHATWOOT_BASE_URL"]
TOKEN = os.environ.get("CHATWOOT_API_KEY")
# Fallback: token persistido em arquivo (chmod 600) — necessário quando
# o token do container API está rotacionado.
if not TOKEN or len(TOKEN) < 16:
    token_path = os.environ.get("CHATWOOT_TOKEN_FILE", "/tmp/chatwoot_token")
    if os.path.exists(token_path):
        with open(token_path) as f:
            TOKEN = f.read().strip()
ACCT = int(os.environ.get("CHATWOOT_ACCOUNT_ID", "1"))
INBOX_NAME = "whatsapp-sim"
if not TOKEN:
    raise SystemExit("FATAL: CHATWOOT_API_KEY não definida (env nem /tmp/chatwoot_token)")

HDR = {"api_access_token": TOKEN, "Content-Type": "application/json"}
TIMEOUT = 15.0

# 10 personas com perfis linguísticos por idade (20-90)
PERSONAS: list[dict[str, Any]] = [
    {"slot": 1, "agent": "TRAE",     "nome": "Maria Silva Santos",   "idade": 67, "telefone": "+5534991001001", "cenario": "certidao_casamento"},
    {"slot": 2, "agent": "TRAE",     "nome": "José Pereira Souza",   "idade": 28, "telefone": "+5534991001002", "cenario": "procuracao"},
    {"slot": 3, "agent": "TRAE",     "nome": "Helena Costa Oliveira","idade": 82, "telefone": "+5534991001003", "cenario": "escritura_imovel"},
    {"slot": 4, "agent": "TRAE",     "nome": "Pedro Almeida Lima",   "idade": 45, "telefone": "+5534991001004", "cenario": "registro_nascimento"},
    {"slot": 5, "agent": "TRAE",     "nome": "Lucia Ferreira",       "idade": 55, "telefone": "+5534991001005", "cenario": "certidao_obito"},
    {"slot": 6, "agent": "ANTIGRAV", "nome": "Carlos Mendes",        "idade": 35, "telefone": "+5534991001006", "cenario": "divorcio"},
    {"slot": 7, "agent": "ANTIGRAV", "nome": "Ana Beatriz Rocha",    "idade": 19, "telefone": "+5534991001007", "cenario": "emancipacao"},
    {"slot": 8, "agent": "ANTIGRAV", "nome": "Roberto Carlos",       "idade": 71, "telefone": "+5534991001008", "cenario": "testamento"},
    {"slot": 9, "agent": "ANTIGRAV", "nome": "Sofia Martins",        "idade": 40, "telefone": "+5534991001009", "cenario": "compra_venda_imovel"},
    {"slot": 10,"agent": "ANTIGRAV", "nome": "Antonio José",         "idade": 90, "telefone": "+5534991001010", "cenario": "inventario"},
]

# Perfis linguísticos por idade
def perfil_linguagem(idade: int) -> dict[str, Any]:
    if idade >= 70:
        return {"formal": True, "usa_abrev": False, "emoji": False, "quebra_linha": True, "abreviacao": "senhor/senhora"}
    if idade >= 50:
        return {"formal": True, "usa_abrev": False, "emoji": False, "quebra_linha": False, "abreviacao": "senhor/senhora"}
    if idade >= 30:
        return {"formal": False, "usa_abrev": True, "emoji": False, "quebra_linha": False, "abreviacao": "você"}
    return {"formal": False, "usa_abrev": True, "emoji": True, "quebra_linha": False, "abreviacao": "vc"}


# Diálogos (3 turnos cliente, 2-3 respostas agente) por cenário
DIALOGOS: dict[str, list[dict[str, str]]] = {
    "certidao_casamento": [
        {"client": "bom dia, gostaria de uma informação", "agent": "Olá! Como posso ajudar?"},
        {"client": "preciso da certidão de casamento, quanto custa e quanto tempo demora?", "agent": "A 2ª via da certidão de casamento custa R$ 105,40 e fica pronta em 5 dias úteis."},
        {"client": "preciso ir presencialmente?", "agent": "Pode ser presencial ou online pelo site. Online leva 5 dias úteis, presencial é no mesmo dia."},
    ],
    "procuracao": [
        {"client": "oi, queria fazer uma procuração", "agent": "Olá! Procuração para qual finalidade?"},
        {"client": "pra representar eu num negócio de carro", "agent": "Para procuração de veículo, traga RG, CPF e documento do veículo. Valor: R$ 89,70."},
        {"client": "tem horário amanhã?", "agent": "Atendemos de segunda a sexta, 8h às 17h. Não precisa agendar."},
    ],
    "escritura_imovel": [
        {"client": "Boa tarde. Gostaria de informação sobre escritura de imóvel.", "agent": "Boa tarde! Qual o tipo: compra e venda, doação ou permuta?"},
        {"client": "Compra e venda. É um apartamento no Centro.", "agent": "Para escritura de compra e venda, traga RG, CPF, certidão de matrícula atualizada e o contrato. Valor depende do valor venal."},
        {"client": "O imóvel está em R$ 450 mil. Posso levar meus documentos amanhã?", "agent": "Pode sim! Traga também o comprovante de residência e certidão de quitação do IPTU. Estaremos abertos das 8h às 17h."},
    ],
    "registro_nascimento": [
        {"client": "oi, meu bebe nasceu ontem e nao sei o que fazer pra registrar", "agent": "Parabéns! O registro pode ser feito em até 15 dias. Traga: RG/CPF dos pais, certidão de casamento (se houver) e declaração do hospital."},
        {"client": "nao sou casada", "agent": "Sem problema. Pode ser reconhecida no ato. Compareça com testemunhas (2) e documentos."},
        {"client": "tem custo?", "agent": "É gratuito diretamente no cartório. Prazo: até 5 dias úteis."},
    ],
    "certidao_obito": [
        {"client": "boa tarde, meu pai faleceu ontem. preciso da certidao de obito", "agent": "Sinto muito pela perda. A certidão é emitida automaticamente pelo cartório de registro civil. Se for aqui da cidade, fica pronta em 2 dias úteis."},
        {"client": "tem algum custo pra emitir a segunda via depois?", "agent": "A 2ª via custa R$ 46,80. Pode solicitar presencialmente ou pelo site do cartório."},
    ],
    "divorcio": [
        {"client": "oi, gostaria de informações sobre divorcio", "agent": "Olá! Divórcio consensual (sem menores) pode ser feito em cartório. Precisa de: certidão de casamento atualizada, RG e CPF de ambos, e advogado."},
        {"client": "tem um filho de 5 anos", "agent": "Com menor envolvido, o processo é judicial (Vara de Família). Posso indicar a documentação inicial se quiser."},
        {"client": "por enquanto só informação mesmo, obrigada", "agent": "Estamos à disposição. Quando decidir prosseguir, busque orientação de um advogado de família."},
    ],
    "emancipacao": [
        {"client": "oi, tenho 19 anos e quero me emancipar", "agent": "Olá! Emancipação para qual finalidade? Trabalho, viagem, estudo?"},
        {"client": "trabalho, ja tenho emprego fixo", "agent": "Para emancipação por exercício de emprego, traga: RG, CPF, comprovante de renda, carteira de trabalho e certidão de nascimento. Valor: R$ 145,30."},
        {"client": "posso ir amanha?", "agent": "Pode! Traga também um responsável legal (pai/mãe) como anuente. Sem necessidade de agendamento."},
    ],
    "testamento": [
        {"client": "Boa tarde. Gostaria de informações sobre testamento.", "agent": "Boa tarde! Testamento pode ser público (em cartório) ou particular. O público custa a partir de R$ 250 e fica arquivado aqui mesmo."},
        {"client": "Preciso ir presencialmente quantas vezes?", "agent": "Duas vezes: uma para orientação e assinatura da minuta, outra (após 5 dias) para confirmação e assinatura final. Traga RG, CPF e certidão de casamento."},
    ],
    "compra_venda_imovel": [
        {"client": "Boa tarde, estou comprando um apartamento e preciso fazer a escritura", "agent": "Boa tarde! Traga: RG, CPF, certidão de matrícula atualizada (30 dias), contrato e comprovante de pagamento do ITBI."},
        {"client": "O ITBI eu pago aqui?", "agent": "Não, o ITBI é pago na Prefeitura. Após o pagamento, traga o comprovante aqui para a escritura."},
        {"client": "Quanto fica a escritura para imóvel de 600 mil?", "agent": "Para imóvel de R$ 600.000,00, os emolumentos ficam em torno de R$ 4.850,00 + ISS. Posso calcular exato se quiser agendar."},
    ],
    "inventario": [
        {"client": "Bom dia, meu pai faleceu e precisamos fazer inventario", "agent": "Bom dia, sinto muito. Inventário pode ser extrajudicial (em cartório) se todos os herdeiros forem maiores e concordarem, sem testamento."},
        {"client": "somos 3 irmaos, todos maiores", "agent": "Ótimo. Traga: certidão de óbito, certidão de casamento do falecido, RG/CPF dos herdeiros, certidão negativa de testamento e relação de bens. Prazo: 60-90 dias."},
        {"client": "tem custo inicial?", "agent": "Custo depende do valor do patrimônio. Para inventário de até R$ 500 mil, fica em torno de R$ 3.200,00. Posso passar valor exato com a relação de bens."},
    ],
}


# ---------------------------------------------------------------------------
# PII sintético determinístico (sem Faker; determinístico + auditável)
# ---------------------------------------------------------------------------
def cpf_sintetico(seed: int) -> str:
    """Gera CPF no formato XXX.XXX.XXX-XX com dígitos calculados."""
    rng = random.Random(seed)
    base = [rng.randint(0, 9) for _ in range(9)]
    # DV1
    s = sum(base[i] * (10 - i) for i in range(9))
    d1 = (s * 10) % 11
    if d1 == 10:
        d1 = 0
    # DV2
    base.append(d1)
    s = sum(base[i] * (11 - i) for i in range(10))
    d2 = (s * 10) % 11
    if d2 == 10:
        d2 = 0
    base.append(d2)
    return f"{base[0]}{base[1]}{base[2]}.{base[3]}{base[4]}{base[5]}.{base[6]}{base[7]}{base[8]}-{d1}{d2}"


def rg_sintetico(seed: int) -> str:
    rng = random.Random(seed + 100)
    n = [rng.randint(0, 9) for _ in range(8)]
    return f"MG-{n[0]}{n[1]}.{n[2]}{n[3]}{n[4]}.{n[5]}{n[6]}{n[7]}"


def email_sintetico(nome: str, seed: int) -> str:
    slug = re.sub(r"[^a-z]", "", nome.lower().replace(" ", "."))
    rng = random.Random(seed + 200)
    dominios = ["example.com", "fake-mail.br", "sintetico.dev"]
    return f"{slug}{rng.randint(10, 99)}@{rng.choice(dominios)}"


def pii_mascarado(cpf: str) -> str:
    """Mascara CPF mantendo só primeiros 3 e últimos 2 dígitos."""
    return f"{cpf[:3]}.***.***-{cpf[-2:]}"


# ---------------------------------------------------------------------------
# Chatwoot helpers
# ---------------------------------------------------------------------------
def _get(path: str, **kw) -> dict[str, Any]:
    r = httpx.get(f"{BASE}{path}", headers=HDR, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    r = httpx.post(f"{BASE}{path}", headers=HDR, json=payload, timeout=TIMEOUT)
    if r.status_code >= 400:
        print(f"POST {path} → {r.status_code}: {r.text[:300]}", file=sys.stderr)
    r.raise_for_status()
    return r.json()


def ensure_inbox() -> int:
    """Garante que a inbox whatsapp-sim existe; retorna id."""
    data = _get(f"/api/v1/accounts/{ACCT}/inboxes")
    payload = data.get("payload", data) if isinstance(data, dict) else data
    for ib in payload:
        if ib.get("name") == INBOX_NAME:
            return ib["id"]
    created = _post(
        f"/api/v1/accounts/{ACCT}/inboxes",
        {"name": INBOX_NAME, "channel": {"type": "api", "webhook_url": ""}},
    )
    payload = created.get("payload", created) if isinstance(created, dict) else created
    return payload["id"]


def _unwrap(d: dict[str, Any]) -> dict[str, Any]:
    """Desempacota resposta Chatwoot: top-level ou {payload: ...}."""
    if isinstance(d, dict) and "payload" in d and isinstance(d["payload"], dict):
        return d["payload"]
    return d


def create_contact(persona: dict[str, Any]) -> int:
    seed = persona["slot"] * 7919  # primo p/ dispersão
    pii = {
        "cpf": cpf_sintetico(seed),
        "rg": rg_sintetico(seed),
        "email": email_sintetico(persona["nome"], seed),
    }
    contact = _post(
        f"/api/v1/accounts/{ACCT}/contacts",
        {
            "name": persona["nome"],
            "phone_number": persona["telefone"],
            "email": pii["email"],
            "custom_attributes": {
                "idade": persona["idade"],
                "cenario": persona["cenario"],
                "cpf_mascarado": pii_mascarado(pii["cpf"]),
                "rg_mascarado": pii["rg"][:5] + "***",
                "pii_sintetico": True,
                "persona_id": f"sim-{persona['slot']:02d}",
                "agent_owner": persona["agent"],
            },
        },
    )
    payload = _unwrap(contact)
    # payload pode ser {contact: {...}} ou {... direto}
    return (payload.get("contact") or payload)["id"]


def create_conversation(inbox_id: int, contact_id: int) -> int:
    conv = _post(
        f"/api/v1/accounts/{ACCT}/conversations",
        {"inbox_id": inbox_id, "contact_id": contact_id, "status": "open"},
    )
    payload = _unwrap(conv)
    return (payload.get("conversation") or payload)["id"]


def send_message(conversation_id: int, content: str, *, outgoing: bool) -> int:
    msg = _post(
        f"/api/v1/accounts/{ACCT}/conversations/{conversation_id}/messages",
        {"content": content, "message_type": "outgoing" if outgoing else "incoming"},
    )
    payload = _unwrap(msg)
    return payload["id"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
@dataclass
class PersonaResult:
    slot: int
    agent: str
    nome: str
    idade: int
    cenario: str
    contact_id: int
    conversation_id: int
    messages: list[int] = field(default_factory=list)
    cpf_sintetico: str = ""
    cpf_mascarado: str = ""
    error: str | None = None


def run_persona(inbox_id: int, persona: dict[str, Any]) -> PersonaResult:
    seed = persona["slot"] * 7919
    cpf = cpf_sintetico(seed)
    res = PersonaResult(
        slot=persona["slot"],
        agent=persona["agent"],
        nome=persona["nome"],
        idade=persona["idade"],
        cenario=persona["cenario"],
        contact_id=0,
        conversation_id=0,
        cpf_sintetico=cpf,
        cpf_mascarado=pii_mascarado(cpf),
    )
    try:
        res.contact_id = create_contact(persona)
        res.conversation_id = create_conversation(inbox_id, res.contact_id)
        time.sleep(0.3)
        dialogo = DIALOGOS[persona["cenario"]]
        for turno in dialogo:
            mid_in = send_message(res.conversation_id, turno["client"], outgoing=False)
            res.messages.append(mid_in)
            time.sleep(0.2)
            mid_out = send_message(res.conversation_id, turno["agent"], outgoing=True)
            res.messages.append(mid_out)
            time.sleep(0.2)
    except Exception as e:
        res.error = f"{type(e).__name__}: {e}"
    return res


def main() -> None:
    only_slots: set[int] = set()
    for arg in sys.argv[1:]:
        try:
            only_slots.add(int(arg))
        except ValueError:
            pass

    inbox_id = ensure_inbox()
    print(f"[OK] inbox whatsapp-sim id={inbox_id}", flush=True)

    results: list[PersonaResult] = []
    for persona in PERSONAS:
        if only_slots and persona["slot"] not in only_slots:
            continue
        print(
            f"[RUN] slot={persona['slot']:02d} agent={persona['agent']} "
            f"persona='{persona['nome']}' idade={persona['idade']} cenario={persona['cenario']}",
            flush=True,
        )
        r = run_persona(inbox_id, persona)
        if r.error:
            print(f"  [ERR] {r.error}", flush=True)
        else:
            print(
                f"  [OK] contact={r.contact_id} conv={r.conversation_id} msgs={len(r.messages)} cpf_mascarado={r.cpf_mascarado}",
                flush=True,
            )
        results.append(r)

    summary = [asdict(r) for r in results]
    out_path = "/tmp/chatwoot_sim_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[DONE] {len(results)} personas → {out_path}", flush=True)
    ok = sum(1 for r in results if not r.error)
    print(f"[STATS] ok={ok}/{len(results)}", flush=True)


if __name__ == "__main__":
    main()