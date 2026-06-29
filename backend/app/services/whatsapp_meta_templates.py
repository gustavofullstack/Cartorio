"""Templates WhatsApp Business API (Meta) — B15.

Templates sao mensagens PRE-APROVADAS pelo Meta/WhatsApp que podem
ser enviadas FORA da janela de 24h (proativo). Tipos suportados:

- UTILITY: transacional (confirmação, lembrete, atualização)
- MARKETING: promocional (com restrições)
- AUTHENTICATION: OTP / códigos de verificação

Cada template tem:
- name (lowercase, snake_case, <= 512 chars)
- category (UTILITY | MARKETING | AUTHENTICATION)
- language (pt-BR)
- components: header (text/image/document) + body + footer + buttons
- variables: {{1}}, {{2}}, ... para personalizacao

Uso:
    from app.services.whatsapp_meta_templates import META_TEMPLATES
    for t in META_TEMPLATES:
        whatsapp_api.create_template(t.name, t.category, t.components)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


TemplateCategory = Literal["UTILITY", "MARKETING", "AUTHENTICATION"]
ComponentType = Literal["HEADER", "BODY", "FOOTER", "BUTTONS"]


@dataclass(frozen=True)
class TemplateComponent:
    """Componente de um template Meta (header/body/footer/buttons)."""

    type: ComponentType
    text: str | None = None  # para HEADER (text) ou BODY ou FOOTER
    format: str | None = None  # para HEADER: TEXT, IMAGE, DOCUMENT, VIDEO
    buttons: tuple[dict, ...] = field(default_factory=tuple)  # para BUTTONS
    example: str | None = None  # exemplo de uso


@dataclass(frozen=True)
class MetaTemplate:
    """Template WhatsApp Business API."""

    name: str  # snake_case lowercase, <= 512 chars
    category: TemplateCategory
    language: str = "pt_BR"
    components: tuple[TemplateComponent, ...] = field(default_factory=tuple)
    description: str = ""  # descricao interna (NAO eh o template Meta)


# ============================================================================
# 1. CONFIRMACAO AGENDAMENTO
# ============================================================================

TEMPLATE_AGENDAMENTO_CONFIRMADO = MetaTemplate(
    name="agendamento_confirmado",
    category="UTILITY",
    description="Confirma agendamento de servico cartorario",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="📅 Agendamento Confirmado",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Seu agendamento no Cartório 2º Notas de Uberlândia foi confirmado:\n\n"
                "📋 *Serviço:* {{2}}\n"
                "📅 *Data:* {{3}}\n"
                "🕐 *Horário:* {{4}}\n"
                "🔖 *Protocolo:* {{5}}\n\n"
                "Enviaremos um lembrete 24h antes. Em caso de imprevistos, "
                "responda esta mensagem ou ligue (34) 3250-XXXX."
            ),
            example="Ex: Joao Silva | Certidao Negativa | 15/07/2026 | 14:30 | PROT-2026000123",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Cartório 2º Notas de Uberlândia — 2notasudi.com.br",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {
                    "type": "URL",
                    "text": "Ver no site",
                    "url": "https://2notasudi.com.br/agendamento/{{1}}",
                    "example": ["PROT-2026000123"],
                },
                {
                    "type": "PHONE_NUMBER",
                    "text": "Ligar",
                    "phone_number": "+553432500000",
                },
            ),
        ),
    ),
)


# ============================================================================
# 2. LEMBRETE AGENDAMENTO
# ============================================================================

TEMPLATE_AGENDAMENTO_LEMBRETE = MetaTemplate(
    name="agendamento_lembrete",
    category="UTILITY",
    description="Lembrete 24h antes do agendamento",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="⏰ Lembrete de Agendamento",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Passando para lembrar do seu agendamento *amanhã*:\n\n"
                "📋 *Serviço:* {{2}}\n"
                "📅 *Data:* {{3}}\n"
                "🕐 *Horário:* {{4}}\n"
                "📍 *Local:* Rua X, nº Y, Centro, Uberlândia/MG\n\n"
                "Caso não possa comparecer, responda *CANCELAR* para reagendar."
            ),
            example="Ex: Joao Silva | Certidao Negativa | 15/07/2026 | 14:30",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Cartório 2º Notas de Uberlândia",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {"type": "QUICK_REPLY", "text": "Confirmar presença"},
                {"type": "QUICK_REPLY", "text": "Cancelar"},
            ),
        ),
    ),
)


# ============================================================================
# 3. PROTOCOLO CRIADO
# ============================================================================

TEMPLATE_PROTOCOLO_CRIADO = MetaTemplate(
    name="protocolo_criado",
    category="UTILITY",
    description="Notifica criacao de novo protocolo",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="🔖 Protocolo Criado",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Seu protocolo foi criado com sucesso:\n\n"
                "🔖 *Número:* {{2}}\n"
                "📋 *Serviço:* {{3}}\n"
                "💰 *Valor:* R$ {{4}}\n"
                "📅 *Previsão:* {{5}} dias úteis\n\n"
                "Acompanhe o status em: 2notasudi.com.br/consulta/{{2}}"
            ),
            example="Ex: Joao Silva | PROT-2026000123 | Certidao Negativa | 87,50 | 5",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Prazo legal: 5 dias úteis (Provimento CNJ)",
        ),
    ),
)


# ============================================================================
# 4. PROTOCOLO CONCLUIDO
# ============================================================================

TEMPLATE_PROTOCOLO_CONCLUIDO = MetaTemplate(
    name="protocolo_concluido",
    category="UTILITY",
    description="Notifica conclusao + disponibilidade para retirada",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="✅ Documento Pronto",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Seu documento está *pronto* para retirada:\n\n"
                "🔖 *Protocolo:* {{2}}\n"
                "📋 *Serviço:* {{3}}\n"
                "📅 *Concluído em:* {{4}}\n\n"
                "📍 *Retirar em:*\n"
                "Rua X, nº Y, Centro, Uberlândia/MG\n"
                "🕐 Horário: 08h00-17h00 (seg-sex)\n\n"
                "Documentos necessários para retirada:\n"
                "• RG e CPF (originais)"
            ),
            example="Ex: Joao Silva | PROT-2026000123 | Certidao Negativa | 12/07/2026",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Cartório 2º Notas de Uberlândia",
        ),
    ),
)


# ============================================================================
# 5. LGPD SOLICITACAO RECEBIDA
# ============================================================================

TEMPLATE_LGPD_SOLICITACAO_RECEBIDA = MetaTemplate(
    name="lgpd_solicitacao_recebida",
    category="UTILITY",
    description="Confirma recebimento de solicitacao LGPD",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="🔒 Solicitação LGPD Recebida",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Recebemos sua solicitação LGPD:\n\n"
                "📋 *Direito exercido:* {{2}}\n"
                "🔖 *Protocolo:* {{3}}\n"
                "📅 *Prazo legal:* até 15 dias úteis\n\n"
                "Nossa equipe entrará em contato para confirmar os procedimentos.\n\n"
                "Em caso de dúvidas: dpo@2notasudi.com.br"
            ),
            example="Ex: Joao Silva | Direito ao Esquecimento | LGPD-2026-001234",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Lei 13.709/2018 — LGPD",
        ),
    ),
)


# ============================================================================
# 6. PAGAMENTO CONFIRMADO
# ============================================================================

TEMPLATE_PAGAMENTO_CONFIRMADO = MetaTemplate(
    name="pagamento_confirmado",
    category="UTILITY",
    description="Confirma recebimento de pagamento",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="💰 Pagamento Confirmado",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Confirmamos o recebimento do seu pagamento:\n\n"
                "💰 *Valor:* R$ {{2}}\n"
                "🔖 *Protocolo:* {{3}}\n"
                "📅 *Data:* {{4}}\n"
                "💳 *Forma:* {{5}}\n\n"
                "Seu serviço será processado em breve. "
                "Acompanhe em 2notasudi.com.br/consulta/{{3}}"
            ),
            example="Ex: Joao Silva | 87,50 | PROT-2026000123 | 10/07/2026 | PIX",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Comprovante enviado por email",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {
                    "type": "URL",
                    "text": "Baixar comprovante",
                    "url": "https://2notasudi.com.br/comprovante/{{1}}.pdf",
                    "example": ["PROT-2026000123"],
                },
            ),
        ),
    ),
)


# ============================================================================
# 7. OTP AUTENTICACAO
# ============================================================================

TEMPLATE_AUTH_OTP = MetaTemplate(
    name="auth_otp",
    category="AUTHENTICATION",
    description="OTP para autenticacao no portal do cartorio",
    components=(
        TemplateComponent(
            type="BODY",
            text=(
                "{{1}} é o seu código de verificação para acessar o portal do "
                "Cartório 2º Notas de Uberlândia.\n\n"
                "Este código expira em {{2}} minutos."
            ),
            example="Ex: 123456 | 10",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Não compartilhe este código com ninguém.",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {
                    "type": "URL",
                    "text": "Abrir portal",
                    "url": "https://portal.2notasudi.com.br/auth?code={{1}}",
                    "example": ["123456"],
                },
            ),
        ),
    ),
)


# ============================================================================
# 8. BOAS VINDAS PRIMEIRO CONTATO
# ============================================================================

TEMPLATE_BOAS_VINDAS = MetaTemplate(
    name="boas_vindas",
    category="MARKETING",
    description="Boas vindas ao primeiro contato",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="👋 Bem-vindo ao Cartório 2º Notas",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Sou o *Pietra*, assistente virtual do Cartório 2º Notas de Uberlândia. "
                "Posso te ajudar com:\n\n"
                "📜 Certidões (negativa, positiva, casamento)\n"
                "🏠 Escrituras (compra, venda, doação)\n"
                "✍️ Procurações e autenticações\n"
                "📅 Agendamentos\n"
                "🔍 Consulta de protocolos\n\n"
                "Como posso te ajudar hoje?"
            ),
            example="Ex: Joao Silva",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Cartório 2º Notas — 2notasudi.com.br",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {"type": "QUICK_REPLY", "text": "Ver serviços"},
                {"type": "QUICK_REPLY", "text": "Agendar"},
                {"type": "QUICK_REPLY", "text": "Falar com humano"},
            ),
        ),
    ),
)


# ============================================================================
# 9. BLACK FRIDAY / PROMO SERVICOS
# ============================================================================

TEMPLATE_PROMO_SERVICOS = MetaTemplate(
    name="promo_servicos",
    category="MARKETING",
    description="Promocao de servicos cartorarios",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="🎉 Promoção Especial",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "No mês de {{2}}, o Cartório 2º Notas está com condições especiais em:\n\n"
                "📜 Certidões: {{3}}\n"
                "🏠 Escrituras: {{4}}\n"
                "✍️ Autenticações: {{5}}\n\n"
                "Válido até {{6}}. Agende pelo nosso portal ou responda esta mensagem."
            ),
            example="Ex: Joao Silva | julho/2026 | 10% off | 15% off | 20% off | 31/07",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Promoção sujeita a alterações",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {"type": "QUICK_REPLY", "text": "Quero aproveitar"},
                {"type": "QUICK_REPLY", "text": "Falar com humano"},
            ),
        ),
    ),
)


# ============================================================================
# 10. PESQUISA SATISFACAO POS ATENDIMENTO
# ============================================================================

TEMPLATE_PESQUISA_SATISFACAO = MetaTemplate(
    name="pesquisa_satisfacao",
    category="UTILITY",
    description="Pesquisa NPS apos atendimento",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="⭐ Avalie nosso atendimento",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}! 👋\n\n"
                "Obrigado por utilizar o Cartório 2º Notas de Uberlândia. "
                "Como você avaliaria nosso atendimento no protocolo {{2}}?\n\n"
                "Responda com um número de 0 a 10, onde:\n"
                "• 0-6 = insatisfeito\n"
                "• 7-8 = satisfeito\n"
                "• 9-10 = muito satisfeito"
            ),
            example="Ex: Joao Silva | PROT-2026000123",
        ),
        TemplateComponent(
            type="FOOTER",
            text="Sua opinião nos ajuda a melhorar!",
        ),
        TemplateComponent(
            type="BUTTONS",
            buttons=(
                {"type": "QUICK_REPLY", "text": "0"},
                {"type": "QUICK_REPLY", "text": "5"},
                {"type": "QUICK_REPLY", "text": "10"},
            ),
        ),
    ),
)


# ============================================================================
# 11. LGPD ESQUECIMENTO CONFIRMADO
# ============================================================================

TEMPLATE_LGPD_ESQUECIMENTO_CONFIRMADO = MetaTemplate(
    name="lgpd_esquecimento_confirmado",
    category="UTILITY",
    description="Confirma conclusao do direito ao esquecimento",
    components=(
        TemplateComponent(
            type="HEADER",
            format="TEXT",
            text="🔒 Dados Anonimizados",
        ),
        TemplateComponent(
            type="BODY",
            text=(
                "Olá {{1}}. 👋\n\n"
                "Conforme LGPD art. 18 VI, seus dados pessoais foram anonimizados em nosso sistema.\n\n"
                "🔖 *Protocolo:* {{2}}\n"
                "📅 *Concluído em:* {{3}}\n\n"
                "⚠️ *Importante:* dados de protocolos já concluídos são mantidos por "
                "5 anos conforme Provimento CNJ 74/2018, mesmo após anonimização do cadastro.\n\n"
                "Dúvidas: dpo@2notasudi.com.br"
            ),
            example="Ex: Joao Silva | LGPD-2026-001234 | 12/07/2026",
        ),
        TemplateComponent(
            type="FOOTER",
            text="LGPD — Lei 13.709/2018",
        ),
    ),
)


# ============================================================================
# CATALOGO COMPLETO (11 templates)
# ============================================================================

META_TEMPLATES: tuple[MetaTemplate, ...] = (
    TEMPLATE_AGENDAMENTO_CONFIRMADO,
    TEMPLATE_AGENDAMENTO_LEMBRETE,
    TEMPLATE_PROTOCOLO_CRIADO,
    TEMPLATE_PROTOCOLO_CONCLUIDO,
    TEMPLATE_LGPD_SOLICITACAO_RECEBIDA,
    TEMPLATE_PAGAMENTO_CONFIRMADO,
    TEMPLATE_AUTH_OTP,
    TEMPLATE_BOAS_VINDAS,
    TEMPLATE_PROMO_SERVICOS,
    TEMPLATE_PESQUISA_SATISFACAO,
    TEMPLATE_LGPD_ESQUECIMENTO_CONFIRMADO,
)


def get_template_by_name(name: str) -> MetaTemplate | None:
    """Busca template por nome (case-insensitive)."""
    name_lower = name.lower()
    for template in META_TEMPLATES:
        if template.name.lower() == name_lower:
            return template
    return None


def get_templates_by_category(category: TemplateCategory) -> tuple[MetaTemplate, ...]:
    """Filtra templates por categoria."""
    return tuple(t for t in META_TEMPLATES if t.category == category)
