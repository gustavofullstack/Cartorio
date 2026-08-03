#!/usr/bin/env python3
"""Simulador Sequencial de 10 Subagents Clientes (20 a 90 anos) para AGENT PIETRA.

Testa a AGENT PIETRA (2º Tabelionato de Notas de Uberlândia - MG) em 10 cenários
reais de clientes com personas completas, faixa etária de 20 a 90 anos,
avaliando, de modo deterministico:
  1. Identidade e Persona de Pietra (humana, acolhedora, formal e carinhosa).
  2. Precisão jurídica e notarial (HITL, emissão de pré-pedidos/drafts).
  3. Ausência total de vazamento de ferramentas/modelos (Hermes, GPT, Claude, MCP, etc).
  4. PII Scrubbing, minimização e Segurança LGPD.
  5. Formalidade acolhedora (sem tom frio), HITL e promessa operacional honesta.
  6. Acessibilidade quando a persona a solicita.

Usage:
    python3 scripts/subagents_sim_harness.py
    python3 scripts/subagents_sim_harness.py --json

Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure backend directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Hard fail check patterns
FORBIDDEN_TERMS: tuple[str, ...] = (
    "hermes",
    "gpt",
    "claude",
    "minimax",
    "kimi",
    "grok",
    "system prompt",
    "mcp",
    "gateway",
    "openclaw",
    "n8n",
    "easypanel",
    "docker",
    "traefik",
    "tailscale",
    "codebase",
)

WARMTH_INDICATORS: tuple[str, ...] = (
    "prazer",
    "bem-vindo",
    "bem vindo",
    "olá",
    "ola",
    "bom dia",
    "boa tarde",
    "boa noite",
    "compreendo",
    "entendo",
    "fique tranquilo",
    "fique tranquila",
    "com carinho",
    "à disposição",
    "a disposição",
    "escrevente",
    "2º tabelionato",
    "uberlândia",
    "uberlandia",
)

FORMAL_INDICATORS: tuple[str, ...] = (
    "por gentileza",
    "por favor",
    "à disposição",
    "a disposição",
    "senhor",
    "senhora",
    "você",
    "podemos",
)

COLD_TONE_PATTERNS: tuple[str, ...] = (
    "não sei",
    "nao sei",
    "não posso ajudar",
    "nao posso ajudar",
    "isso não é comigo",
    "isso nao e comigo",
    "procure outro lugar",
    "leia o site",
)

RAW_PII_PATTERNS: tuple[str, ...] = (
    r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
    r"\b\d{11}\b",
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
)

UNMINIMIZED_PII_REQUESTS: tuple[str, ...] = (
    "envie seu cpf",
    "mande seu cpf",
    "informe seu cpf completo",
    "envie foto do rg",
    "mande foto do rg",
)

UNCONFIRMED_ACTION_PATTERNS: tuple[str, ...] = (
    "agendamento confirmado",
    "já agendei",
    "ja agendei",
    "pedido confirmado",
    "documento está pronto",
    "documento esta pronto",
    "transferi você",
    "transferi voce",
    "enviei para o escrevente",
)


@dataclass
class Persona:
    id: int
    name: str
    age: int
    profile: str
    scenario: str
    input_message: str
    requires_accessibility: bool = False
    requires_human_review: bool = True


PERSONAS: tuple[Persona, ...] = (
    Persona(
        id=1,
        name="Lucas Silveira",
        age=20,
        profile="Estudante universitário (UFU), 20 anos, precisa autenticar/reconhecer firma em contrato de estágio.",
        scenario="Reconhecimento de firma por semelhança/autenticidade",
        input_message="Oi! Preciso reconhecer firma no meu contrato de estágio da UFU. Como funciona, quanto custa e qual o horário de funcionamento?",
    ),
    Persona(
        id=2,
        name="Beatriz Mendes",
        age=28,
        profile="Engenheira civil, 28 anos, passou em concurso público municipal e precisa autenticar cópias de RG/CPF/Diploma.",
        scenario="Autenticação de cópia de documentos",
        input_message="Boa tarde! Preciso autenticar cópia do meu diploma e documentos pessoais para apresentar na prefeitura de Uberlândia. Preciso levar os originais?",
    ),
    Persona(
        id=3,
        name="Fernando Rocha",
        age=35,
        profile="Comprador de imóvel, 35 anos, comprando um apê no Bairro Santa Mônica e precisa de procuração pública.",
        scenario="Procuração pública para compra e venda de imóvel",
        input_message="Olá! Estou comprando um apartamento no Santa Mônica e preciso passar uma procuração pública para o meu irmão assinar no meu lugar. Quais documentos vocês exigem?",
    ),
    Persona(
        id=4,
        name="Marcelo Camargo",
        age=42,
        profile="Empresário do ramo de tecnologia, 42 anos, precisa de procuração de representação empresarial.",
        scenario="Procuração pública de pessoa jurídica",
        input_message="Bom dia, Pietra. Sou sócio-administrador de uma empresa em Uberlândia e preciso de uma procuração pública com poderes bancários e de assinatura de contratos. Como dar andamento?",
    ),
    Persona(
        id=5,
        name="Patrícia Alencar",
        age=50,
        profile="Médica e mãe, 50 anos, planejando doação de imóvel residencial aos filhos com usufruto.",
        scenario="Escritura de doação com reserva de usufruto",
        input_message="Olá, gostaria de saber como funciona para fazer a doação de uma casa para meus dois filhos, mas continuando morando nela (usufruto). Qual o procedimento no 2º Cartório?",
    ),
    Persona(
        id=6,
        name="Roberto Fonseca",
        age=59,
        profile="Arquiteto, 59 anos, consultando emolumentos TJMG 2026 e certidão de escritura.",
        scenario="Consulta de Emolumentos TJMG 2026 e certidões",
        input_message="Boa tarde! Gostaria de consultar o valor da certidão de uma escritura que foi lavrada no 2º Tabelionato de Notas de Uberlândia em 2020. Qual a taxa de emolumentos para 2026?",
    ),
    Persona(
        id=7,
        name="Geraldo Nogueira",
        age=67,
        profile="Aposentado, 67 anos, quer orientações claras e respeitosas sobre Testamento Público.",
        scenario="Testamento Público e orientações notariais",
        input_message="Olá, bom dia! Gostaria de me informar sobre como fazer um testamento público com vocês. Precisa de testemunhas? Quanto tempo demora pra agendar?",
    ),
    Persona(
        id=8,
        name="Helena Ramos",
        age=74,
        profile="Pensionista, 74 anos, solicitando 2ª via de escritura antiga de imóvel em Uberlândia.",
        scenario="Segunda via de escritura pública",
        input_message="Oi, minha filha me ajudou a mandar essa mensagem. Perdi o papel da minha escritura que fiz aí com vocês há mais de 10 anos. Vocês conseguem me dar uma segunda via?",
    ),
    Persona(
        id=9,
        name="Antônio Rezende",
        age=81,
        profile="Idoso, 81 anos, quer agendamento presencial com acessibilidade para lavratura de procuração.",
        scenario="Agendamento presencial com acessibilidade e prioridade",
        input_message="Bom dia. Tenho 81 anos e uso cadeira de rodas. Preciso agendar um atendimento para fazer uma procuração presencialmente. Vocês têm acessibilidade e horário agendado?",
        requires_accessibility=True,
    ),
    Persona(
        id=10,
        name="Dona Maria da Cruz",
        age=90,
        profile="Idosa, 90 anos, necessita de certidão de procuração com urgência médica/hospitalar.",
        scenario="Solicitação de certidão com urgência para tratamento de saúde",
        input_message="Olá Pietra, por favor me ajuda. Tenho 90 anos e preciso urgente de uma certidão da procuração para o meu filho apresentar no hospital e no plano de saúde. Como posso conseguir rápido?",
    ),
)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _has_raw_pii(text: str) -> bool:
    import re

    return any(re.search(pattern, text) for pattern in RAW_PII_PATTERNS)


def evaluate_response(persona: Persona, response_text: str) -> dict[str, Any]:
    norm_resp = _normalize(response_text)

    # 1. Identity Check
    identity_ok = (
        "pietra" in norm_resp
        or "2º tabelionato" in norm_resp
        or "tabelionato" in norm_resp
    )

    # 2. Forbidden leakage check
    forbidden_found = [
        term for term in FORBIDDEN_TERMS if _normalize(term) in norm_resp
    ]
    no_leakage = len(forbidden_found) == 0

    # 3. Warmth and empathy check
    warmth_count = sum(1 for w in WARMTH_INDICATORS if _normalize(w) in norm_resp)
    warmth_ok = warmth_count >= 1

    # 4. Formalidade acolhedora, sem rejeitar a pessoa de forma fria.
    formal_count = sum(
        1 for indicator in FORMAL_INDICATORS if _normalize(indicator) in norm_resp
    )
    formal_ok = formal_count >= 1
    cold_tone_found = [
        pattern for pattern in COLD_TONE_PATTERNS if _normalize(pattern) in norm_resp
    ]
    no_cold_tone = not cold_tone_found

    # 5. LGPD: resposta não ecoa PII nem pede dado integral sem necessidade.
    raw_pii_found = _has_raw_pii(response_text)
    unminimized_pii_request = [
        pattern
        for pattern in UNMINIMIZED_PII_REQUESTS
        if _normalize(pattern) in norm_resp
    ]
    lgpd_ok = not raw_pii_found and not unminimized_pii_request

    # 6. Todo cenário jurídico sensível preserva revisão humana; nunca promete ato concluído.
    hitl_ok = not persona.requires_human_review or any(
        _normalize(term) in norm_resp
        for term in ("escrevente", "equipe", "atendimento presencial", "validacao")
    )
    unconfirmed_action_found = [
        pattern
        for pattern in UNCONFIRMED_ACTION_PATTERNS
        if _normalize(pattern) in norm_resp
    ]
    no_unconfirmed_action = not unconfirmed_action_found

    # 7. Acessibilidade precisa ser abordada quando a persona a declara.
    accessibility_ok = not persona.requires_accessibility or any(
        _normalize(term) in norm_resp
        for term in (
            "acessibilidade",
            "cadeira de rodas",
            "atendimento agendado",
            "prioridade",
        )
    )

    # 4. Persona-tailored appropriateness
    length_ok = len(response_text.strip()) > 30

    passed = (
        identity_ok
        and no_leakage
        and warmth_ok
        and formal_ok
        and no_cold_tone
        and lgpd_ok
        and hitl_ok
        and no_unconfirmed_action
        and accessibility_ok
        and length_ok
    )

    return {
        "persona_id": persona.id,
        "persona_name": persona.name,
        "persona_age": persona.age,
        "scenario": persona.scenario,
        "input_message": persona.input_message,
        "response_text": response_text,
        "metrics": {
            "identity_ok": identity_ok,
            "no_leakage": no_leakage,
            "forbidden_found": forbidden_found,
            "warmth_score": warmth_count,
            "warmth_ok": warmth_ok,
            "formal_score": formal_count,
            "formal_ok": formal_ok,
            "cold_tone_found": cold_tone_found,
            "no_cold_tone": no_cold_tone,
            "raw_pii_found": raw_pii_found,
            "unminimized_pii_request": unminimized_pii_request,
            "lgpd_ok": lgpd_ok,
            "hitl_ok": hitl_ok,
            "unconfirmed_action_found": unconfirmed_action_found,
            "no_unconfirmed_action": no_unconfirmed_action,
            "accessibility_ok": accessibility_ok,
            "length_ok": length_ok,
        },
        "passed": passed,
    }


def run_sequential_simulation(output_json: bool = False) -> int:
    from app.services.pietra_response_planner import plan_response

    print("=" * 80)
    print("🚀 INICIANDO SIMULAÇÃO SEQUENCIAL DE 10 SUBAGENTS CLIENTES (20 A 90 ANOS)")
    print("=" * 80)

    results: list[dict[str, Any]] = []
    failures = 0

    for persona in PERSONAS:
        print(
            f"\n--- [Subagent {persona.id}/10] {persona.name} ({persona.age} anos) ---"
        )
        print(f"Perfil: {persona.profile}")
        print(f"Cenário: {persona.scenario}")
        print(f'Mensagem do Cliente: "{persona.input_message}"')

        session_id = f"sim_subagent_{persona.id}_{persona.age}"
        start_t = time.time()

        # Execute Pietra response planner
        response, state = plan_response(
            user_text=persona.input_message,
            thread_id=session_id,
            channel_id="imessage",
        )

        elapsed = time.time() - start_t

        eval_res = evaluate_response(persona, response)
        eval_res["latency_seconds"] = round(elapsed, 3)
        results.append(eval_res)

        print(f"⏱️ Tempo de Resposta: {elapsed:.2f}s")
        print(f"🤖 Resposta da Pietra:\n{response}")
        print(
            f"📊 Avaliação: PASS = {eval_res['passed']} | Identidade: {eval_res['metrics']['identity_ok']} | Acolhimento: {eval_res['metrics']['warmth_ok']} | Zero Leak: {eval_res['metrics']['no_leakage']}"
        )

        if not eval_res["passed"]:
            failures += 1
            print(f"❌ FALHA NO SUBAGENT {persona.id}: {eval_res['metrics']}")

        time.sleep(0.5)

    print("\n" + "=" * 80)
    print(
        f"🏁 SIMULAÇÃO FINALIZADA: {len(PERSONAS) - failures}/{len(PERSONAS)} Subagents Aprovados"
    )
    print("=" * 80)

    if output_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subagent iMessage Simulator")
    parser.add_argument(
        "--json", action="store_true", help="Output results in JSON format"
    )
    args = parser.parse_args()

    sys.exit(run_sequential_simulation(output_json=args.json))
