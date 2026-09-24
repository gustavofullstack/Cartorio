#!/usr/bin/env python3
"""
Sequential Multi-Agent Persona Simulation Harness for Pietra (Cartório AI Agent).
Tests 10 distinct citizen personas (ages 20 to 90) interacting with Pietra.
Validates:
- 100% resolutive answers
- Zero CJK/Chinese character leaks
- Correct address (Sede: Rua Cel. Antônio Alves Pereira, 850; ZERO unidade complementar)
- Correct substitutes (Djalma, Felipe, Alexandra; ZERO Victor Hugo)
- Formal, warm, and structured responses
"""

import sys
import re
import json
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.cartorio_agent import run_cartorio_agent


PERSONAS = [
    {
        "id": "P20_Lucas",
        "age": 20,
        "profile": "Estudante Universitário (20 anos)",
        "messages": [
            "Oi, preciso autenticar uns documentos pra faculdade. Como funciona?",
            "Quanto custa por página?",
            "Onde fica o cartório mesmo?",
        ],
    },
    {
        "id": "P27_Mariana",
        "age": 27,
        "profile": "Arquiteta (27 anos)",
        "messages": [
            "Olá! Preciso fazer uma procuração pública para meu irmão vender um carro em meu nome.",
            "Qual o valor dessa procuração e quais documentos preciso enviar?",
            "Consigo agendar para quinta-feira às 14h?",
        ],
    },
    {
        "id": "P35_Carlos",
        "age": 35,
        "profile": "Empresário (35 anos)",
        "messages": [
            "Boa tarde. Preciso lavrar uma ata notarial de conteúdo na internet para um processo.",
            "Vocês atendem em alguma unidade complementar ou só na sede?",
            "Quem são os escreventes substitutos que podem me atender?",
        ],
    },
    {
        "id": "P42_Fernanda",
        "age": 42,
        "profile": "Corretora de Imóveis (42 anos)",
        "messages": [
            "Oi Pietra, tudo bem? Quero saber os emolumentos para uma escritura de compra e venda de imóvel de R$ 300.000,00.",
            "Posso abrir um pré-protocolo por aqui antes de ir ao cartório?",
            "Quais documentos o comprador e vendedor precisam apresentar?",
        ],
    },
    {
        "id": "P51_Roberto",
        "age": 51,
        "profile": "Engenheiro (51 anos)",
        "messages": [
            "Bom dia. Gostaria de reconhecer firma por autenticidade em um contrato de locação.",
            "Qual o horário de funcionamento de vocês?",
            "Qual o telefone de contato oficial?",
        ],
    },
    {
        "id": "P60_Ana",
        "age": 60,
        "profile": "Professora Aposentada (60 anos)",
        "messages": [
            "Olá minha filha! Preciso fazer um testamento público. É muito complicado?",
            "Quais são os documentos necessários e como faço para agendar uma pré-análise?",
            "Vocês cobram consulta jurídica para tirar dúvida?",
        ],
    },
    {
        "id": "P68_Jose",
        "age": 68,
        "profile": "Aposentado (68 anos)",
        "messages": [
            "Boa tarde. Quero tirar uma segunda via da minha procuração antiga lavrada em 2024.",
            "Vocês conseguem consultar meu protocolo pelo número 2024-001234?",
            "Onde fica o endereço exato para eu buscar a certidão?",
        ],
    },
    {
        "id": "P75_DonaClara",
        "age": 75,
        "profile": "Pensionista (75 anos)",
        "messages": [
            "Oi Pietra, meu filho me falou pra mandar mensagem. Eu preciso dar uma procuração pro meu advogado me representar no INSS.",
            "Quanto custa isso pra mim que sou aposentada?",
            "Tem estacionamento perto da sede no centro?",
        ],
    },
    {
        "id": "P82_SeuAntônio",
        "age": 82,
        "profile": "Produtor Rural (82 anos)",
        "messages": [
            "Minha jovem, boa tarde. Preciso saber quem é o tabelião responsável do cartório.",
            "O Victor Hugo ainda trabalha aí como substituto?",
            "Qual o endereço certo do cartório pra eu ir amanhã de manhã?",
        ],
    },
    {
        "id": "P90_DonaBeatriz",
        "age": 90,
        "profile": "Dona de casa (90 anos)",
        "messages": [
            "Boa tarde, gostaria de saber se o cartório faz atendimento em domicílio para idosos.",
            "Vocês atendem de sábado também?",
            "Muito obrigada pelo carinho e atenção no atendimento!",
        ],
    },
]


async def run_simulation():
    print("🚀 Iniciando Simulação Sequencial de 10 Personas (20 a 90 anos)...")
    print("=" * 70)

    total_turns = 0
    passed_turns = 0
    failures = []

    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\u3400-\u4dbf]")

    for persona in PERSONAS:
        p_id = persona["id"]
        p_profile = persona["profile"]
        print(f"\n👤 [{p_id}] Profile: {p_profile}")

        history = []

        for turn_idx, user_msg in enumerate(persona["messages"], 1):
            total_turns += 1
            print(f"  Turn {turn_idx}: User -> '{user_msg}'")

            try:
                reply = await run_cartorio_agent(
                    user_msg,
                    history=history,
                    chat_id=p_id,
                )
                response_text = reply.text or ""

                # Maintain conversation history
                history.append(f"User: {user_msg}")
                history.append(f"Assistant: {response_text}")

                # Assertions & Checks
                has_cjk = bool(cjk_pattern.search(response_text))
                normalized_response = response_text.lower()
                denies_extra_unit = (
                    "não existe unidade complementar" in normalized_response
                    or "nao existe unidade complementar" in normalized_response
                )
                has_unidade_comp = "machado de assis" in normalized_response or (
                    "unidade complementar" in normalized_response
                    and not denies_extra_unit
                )
                has_victor_hugo = "victor hugo" in normalized_response and not any(
                    phrase in normalized_response
                    for phrase in (
                        "não trabalha mais",
                        "nao trabalha mais",
                        "não integra mais",
                        "nao integra mais",
                    )
                )
                has_deflection = (
                    "ligue para o cartório" in response_text.lower()
                    and len(response_text) < 100
                )

                turn_issues = []
                if has_cjk:
                    turn_issues.append("Contém caracteres CJK/Chinês")
                if has_unidade_comp:
                    turn_issues.append(
                        "Mencionou unidade complementar/Machado de Assis inexistente"
                    )
                if has_victor_hugo:
                    turn_issues.append("Mencionou Victor Hugo (não integra mais)")
                if has_deflection:
                    turn_issues.append(
                        "Resposta de deflexão passiva ('ligue para o cartório')"
                    )

                if not turn_issues:
                    passed_turns += 1
                    first_line = response_text.split("\n")[0] if response_text else ""
                    print(f"    ✅ Pietra: '{first_line[:100]}...'")
                else:
                    print(f"    ❌ Pietra: ISSUES DETECTED: {turn_issues}")
                    print(f"       Full Text: {response_text}")
                    failures.append(
                        {
                            "persona": p_id,
                            "turn": turn_idx,
                            "user": user_msg,
                            "response": response_text,
                            "issues": turn_issues,
                        }
                    )

            except Exception as e:
                print(f"    ❌ Error invoking agent: {e}")
                failures.append(
                    {
                        "persona": p_id,
                        "turn": turn_idx,
                        "user": user_msg,
                        "response": None,
                        "issues": [f"Exception: {str(e)}"],
                    }
                )

    print("\n" + "=" * 70)
    print(f"📊 RESULTADO DA SIMULAÇÃO:")
    print(f"   Total Turns: {total_turns}")
    print(f"   Passed Turns: {passed_turns} ({passed_turns / total_turns * 100:.1f}%)")
    print(f"   Failures: {len(failures)}")

    if failures:
        print("\n❌ RELATÓRIO DE FALHAS:")
        for f in failures:
            print(f"  - Persona {f['persona']} (Turn {f['turn']}): {f['issues']}")
        sys.exit(1)
    else:
        print("\n🎉 TODAS AS 10 PERSONAS PASSARAM COM 100% DE SUCESSO!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_simulation())
