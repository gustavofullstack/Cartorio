"""Modelo de Setor/Departamento do Cartório para roteamento HITL.

Cada setor representa uma área de atuação ou departamento interno do cartório
responsável por tipos específicos de atos notariais. O roteamento HITL usa
este modelo para encaminhar atendimentos ao escrevente/setor correto.

Configurável via banco de dados — não hardcodeado no código.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Setor(Base, TimestampMixin):
    """Setor/Departamento do cartório (ex.: Escrituras, Procurações, Reconhecimento de Firma)."""

    __tablename__ = "setores"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_setor_slug"),
        {"comment": "Setores/departamentos do cartório para roteamento HITL"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone_interno: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordem_exibicao: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relacionamento com protocolos via tabela de associação
    # (removido back_populates para evitar erro de FK no modelo Protocolo)
    # protocolos: Mapped[list["Protocolo"]] = relationship(
    #     "Protocolo", back_populates="setor", lazy="dynamic"
    # )

    def __repr__(self) -> str:
        return f"<Setor(id={self.id}, slug={self.slug!r}, nome={self.nome!r})>"


class ProtocoloSetor(Base):
    """Tabela de associação entre Protocolo e Setor (muitos-para-muitos).

    Um protocolo pode envolver múltiplos setores (ex.: escritura + reconhecimento).
    """

    __tablename__ = "protocolo_setores"
    __table_args__ = (
        UniqueConstraint("protocolo_id", "setor_id", name="uq_protocolo_setor"),
    )

    protocolo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("protocolos.id", ondelete="CASCADE"), primary_key=True
    )
    setor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("setores.id", ondelete="CASCADE"), primary_key=True
    )
    principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    criado_em: Mapped[str] = mapped_column(String(30), nullable=False)  # ISO datetime

    def __repr__(self) -> str:
        return f"<ProtocoloSetor(protocolo_id={self.protocolo_id}, setor_id={self.setor_id}, principal={self.principal})>"


# Tipos de ato mapeados para setores (configuração inicial)
# Esta configuração é o default; o admin pode editar via DB/API
SETOR_POR_TIPO_ATO_DEFAULT: dict[str, str] = {
    # Escrituras
    "escritura_compra_venda": "escrituras",
    "escritura_doacao": "escrituras",
    "escritura_sem_conteudo_financeiro": "escrituras",
    "escritura_aditamento_sem_valor": "escrituras",
    "escritura_convencao_condominio": "escrituras",
    "escritura_pacto_divorcio_uniao_estavel": "escrituras",
    "escritura_com_conteudo_financeiro": "escrituras",
    # Procurações
    "procuracao_geral": "procuracoes",
    "procuracao_previdenciaria": "procuracoes",
    "procuracao_com_conteudo_financeiro": "procuracoes",
    "substabelecimento_procuracao": "procuracoes",
    "procuracao_generica": "procuracoes",
    "procuracao": "procuracoes",
    "procuracao_inss": "procuracoes",
    "procuracao_financeira": "procuracoes",
    "procuracao_causa_propria": "procuracoes",
    # Reconhecimento de firma
    "reconhecimento_firma_assinatura": "reconhecimento_firma",
    "reconhecimento_firma_cartao": "reconhecimento_firma",
    "reconhecimento_firma": "reconhecimento_firma",
    "reconhecimento": "reconhecimento_firma",
    "reconhecimento_enot_assina": "reconhecimento_firma",
    # Autenticações
    "autenticacao_copia_folha": "autenticacoes",
    "autenticacao_documento_eletronico": "autenticacoes",
    "autenticacao_digital": "autenticacoes",
    "autenticacao": "autenticacoes",
    "autenticacao_pagina": "autenticacoes",
    "autenticacao_copia": "autenticacoes",
    "autenticacao_digital_cenad": "autenticacoes",
    # Testamentos
    "testamento": "testamentos",
    "testamento_cerrado_a_rogo": "testamentos",
    "testamento_publico": "testamentos",
    "revogacao_testamento": "testamentos",
    "aprovacao_testamento_cerrado": "testamentos",
    "testamento_cerrado_rogo": "testamentos",
    "testamento_generico": "testamentos",
    # Inventários
    "inventario_sem_conteudo_financeiro": "inventarios",
    "inventario_com_partilha": "inventarios",
    "inventario_sem_valor": "inventarios",
    # Certidões
    "certidao_negativa": "certidoes",
    "certidao_positiva": "certidoes",
    "certidao_casamento": "certidoes",
    "certidao_inteiro_teor": "certidoes",
    "certidao_quesitos": "certidoes",
    "certidao_breve_relato": "certidoes",
    # Atas notariais
    "ata_notarial_ate_2_folhas": "atas_notariais",
    "ata_notarial_folha_acrescida": "atas_notariais",
    "ata_notarial_primeira_folha": "atas_notariais",
    "ata_notarial": "atas_notariais",
    # Arquivamento
    "arquivamento": "arquivamento",
    "arquivamentos": "arquivamento",
    # Diligências
    "diligencia_urbana": "diligencias",
    "diligencia_rural": "diligencias",
    "diligencia_outros_limites": "diligencias",
    "diligencias": "diligencias",
    # Apostilamento
    "apostilamento": "apostilamento",
    # Autorizações
    "autorizacao_eletronica_viagem": "autorizacoes",
    # Gratuidade/Isenção
    "gratuidade_isencao": "gratuidade_isencao",
    # Usucapião
    "usucapiao": "usucapiao",
}

# Setores padrão do 2º Ofício de Notas de Uberlândia
SETORES_PADRAO: list[dict[str, str | int | None]] = [
    {
        "slug": "escrituras",
        "nome": "Escrituras",
        "descricao": "Lavratura de escrituras públicas (compra e venda, doação, pacto, divórcio, etc.)",
        "responsavel": "Escrevente de Escrituras",
        "email": "escrituras@2notasudi.com.br",
        "telefone_interno": "ramal 101",
        "ordem_exibicao": 1,
    },
    {
        "slug": "procuracoes",
        "nome": "Procurações",
        "descricao": "Lavratura de procurações públicas (genérica, previdenciária, com conteúdo financeiro)",
        "responsavel": "Escrevente de Procurações",
        "email": "procuracoes@2notasudi.com.br",
        "telefone_interno": "ramal 102",
        "ordem_exibicao": 2,
    },
    {
        "slug": "reconhecimento_firma",
        "nome": "Reconhecimento de Firma",
        "descricao": "Reconhecimento de firma por semelhança e autenticidade; abertura de firma; e-Not Assina",
        "responsavel": "Escrevente de Reconhecimento de Firma",
        "email": "reconhecimento@2notasudi.com.br",
        "telefone_interno": "ramal 103",
        "ordem_exibicao": 3,
    },
    {
        "slug": "autenticacoes",
        "nome": "Autenticações",
        "descricao": "Autenticação de cópias, documentos eletrônicos, autenticação digital CENAD",
        "responsavel": "Escrevente de Autenticações",
        "email": "autenticacoes@2notasudi.com.br",
        "telefone_interno": "ramal 104",
        "ordem_exibicao": 4,
    },
    {
        "slug": "testamentos",
        "nome": "Testamentos",
        "descricao": "Lavratura de testamentos (público, cerrado), aprovação, revogação",
        "responsavel": "Escrevente de Testamentos",
        "email": "testamentos@2notasudi.com.br",
        "telefone_interno": "ramal 105",
        "ordem_exibicao": 5,
    },
    {
        "slug": "inventarios",
        "nome": "Inventários",
        "descricao": "Inventários extrajudiciais (sem conteúdo financeiro, com partilha)",
        "responsavel": "Escrevente de Inventários",
        "email": "inventarios@2notasudi.com.br",
        "telefone_interno": "ramal 106",
        "ordem_exibicao": 6,
    },
    {
        "slug": "certidoes",
        "nome": "Certidões",
        "descricao": "Emissão de certidões (negativa, positiva, casamento, inteiro teor, quesitos)",
        "responsavel": "Escrevente de Certidões",
        "email": "certidoes@2notasudi.com.br",
        "telefone_interno": "ramal 107",
        "ordem_exibicao": 7,
    },
    {
        "slug": "atas_notariais",
        "nome": "Atas Notariais",
        "descricao": "Lavratura de atas notariais (até 2 folhas, folhas acrescidas)",
        "responsavel": "Escrevente de Atas",
        "email": "atas@2notasudi.com.br",
        "telefone_interno": "ramal 108",
        "ordem_exibicao": 8,
    },
    {
        "slug": "arquivamento",
        "nome": "Arquivamento",
        "descricao": "Arquivamento de documentos e processos",
        "responsavel": "Arquivista",
        "email": "arquivamento@2notasudi.com.br",
        "telefone_interno": "ramal 109",
        "ordem_exibicao": 9,
    },
    {
        "slug": "diligencias",
        "nome": "Diligências",
        "descricao": "Diligências urbanas, rurais e outros limites",
        "responsavel": "Oficial de Diligências",
        "email": "diligencias@2notasudi.com.br",
        "telefone_interno": "ramal 110",
        "ordem_exibicao": 10,
    },
    {
        "slug": "apostilamento",
        "nome": "Apostilamento",
        "descricao": "Apostilamento de documentos (Convenção de Haia)",
        "responsavel": "Escrevente de Apostilamento",
        "email": "apostilamento@2notasudi.com.br",
        "telefone_interno": "ramal 111",
        "ordem_exibicao": 11,
    },
    {
        "slug": "autorizacoes",
        "nome": "Autorizações",
        "descricao": "Autorização eletrônica de viagem de menor",
        "responsavel": "Escrevente de Autorizações",
        "email": "autorizacoes@2notasudi.com.br",
        "telefone_interno": "ramal 112",
        "ordem_exibicao": 12,
    },
    {
        "slug": "gratuidade_isencao",
        "nome": "Gratuidade e Isenção",
        "descricao": "Análise de pedidos de gratuidade e isenção de emolumentos",
        "responsavel": "Tabelião / Escrevente responsável",
        "email": "gratuidade@2notasudi.com.br",
        "telefone_interno": "ramal 200",
        "ordem_exibicao": 13,
    },
    {
        "slug": "usucapiao",
        "nome": "Usucapião",
        "descricao": "Usucapião extrajudicial",
        "responsavel": "Escrevente de Usucapião",
        "email": "usucapiao@2notasudi.com.br",
        "telefone_interno": "ramal 113",
        "ordem_exibicao": 14,
    },
]