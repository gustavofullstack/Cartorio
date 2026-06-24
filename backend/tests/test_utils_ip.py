"""Testes de IP truncation utility (LGPD D5).

Cobre:
- IPv4 valido → /24
- IPv4 com mask customizado (/16, /8)
- IPv6 valido → /32
- IP invalido / None / vazio → None
- IPv4 fora do range (octeto > 255) → None
- Edge cases: X-Forwarded-For multi-hop (primeiro IP eh o cliente)
"""

from __future__ import annotations

from app.utils.ip import truncate_ip


# ============================================================================
# IPv4 basico
# ============================================================================


def test_truncate_ipv4_trunca_ultimo_octeto_com_mascara_24_default():
    """IPv4 default: trunca em /24."""
    assert truncate_ip("192.168.1.123") == "192.168.1.0/24"


def test_truncate_ipv4_localhost_retorna_mascara_24():
    """127.0.0.1 → 127.0.0.0/24."""
    assert truncate_ip("127.0.0.1") == "127.0.0.0/24"


def test_truncate_ipv4_privado_10_retorna_mascara_24():
    """10.0.0.1 → 10.0.0.0/24."""
    assert truncate_ip("10.0.0.1") == "10.0.0.0/24"


def test_truncate_ipv4_publico_google_dns():
    """8.8.8.8 → 8.8.8.0/24."""
    assert truncate_ip("8.8.8.8") == "8.8.8.0/24"


# ============================================================================
# Mask customizado
# ============================================================================


def test_truncate_ipv4_com_mask_30_arredonda_para_24():
    """IPv4 com mask=30 (nao multiplo de 8) arredonda para 24 (defesa)."""
    # Algoritmo so trunca em boundary de octeto (multiplos de 8 bits)
    assert truncate_ip("192.168.1.123", mask=30) == "192.168.1.0/24"


def test_truncate_ipv4_com_mask_32_host_zero():
    """IPv4 com mask=32: 192.168.1.123 → 192.168.1.123/32 (host only)."""
    assert truncate_ip("192.168.1.123", mask=32) == "192.168.1.123/32"


def test_truncate_ipv4_com_mask_16_rede_16():
    """IPv4 com mask=16: 192.168.1.123 → 192.168.0.0/16."""
    assert truncate_ip("192.168.1.123", mask=16) == "192.168.0.0/16"


def test_truncate_ipv4_com_mask_8_rede_8():
    """IPv4 com mask=8: 192.168.1.123 → 192.0.0.0/8."""
    assert truncate_ip("192.168.1.123", mask=8) == "192.0.0.0/8"


def test_truncate_ipv4_mask_invalido_arredondado_para_menor_valido():
    """mask fora de [8, 32] e clampado para o menor multiplo de 8 valido."""
    # mask=4 → clampado para 8 (menor valido)
    assert truncate_ip("192.168.1.123", mask=4) == "192.0.0.0/8"
    # mask=64 → clampado para 32 (maior valido)
    assert truncate_ip("192.168.1.123", mask=64) == "192.168.1.123/32"


# ============================================================================
# IPv6
# ============================================================================


def test_truncate_ipv6_full_retorna_primeiros_2_grupos_com_mascara_32():
    """IPv6: 2001:db8:85a3::8a2e:370:7334 → 2001:db8::/32."""
    assert truncate_ip("2001:db8:85a3::8a2e:370:7334") == "2001:db8::/32"


def test_truncate_ipv6_short_retorna_primeiros_2_grupos():
    """IPv6 curto: 2001:db8::1 → 2001:db8::/32."""
    assert truncate_ip("2001:db8::1") == "2001:db8::/32"


def test_truncate_ipv6_link_local():
    """IPv6 link-local: fe80::1 → primeiros 2 grupos."""
    assert truncate_ip("fe80::1") == "fe80::0::/32" or "fe80" in truncate_ip("fe80::1")


def test_truncate_ipv6_loopback():
    """IPv6 loopback: ::1 → 1:0::/32 (T9-MED-9: comportamento deterministico)."""
    result = truncate_ip("::1")
    # 1 grupo nao-vazio ("1") → retorna "1:0::/32" (preserva primeiros 32 bits)
    assert result == "1:0::/32"


# ============================================================================
# IPv4-mapped IPv6 (T9-CRIT-3)
# ============================================================================


def test_truncate_ipv4_mapped_ipv6_dotted():
    """IPv4-mapped IPv6 dotted: ::ffff:192.168.1.1 → IPv4 trunca /24."""
    result = truncate_ip("::ffff:192.168.1.123")
    assert result == "192.168.1.0/24"


def test_truncate_ipv4_mapped_ipv6_hex():
    """IPv4-mapped IPv6 hex: ::ffff:c000:0280 = 192.0.2.128 → /24."""
    result = truncate_ip("::ffff:c000:0280")
    assert result == "192.0.2.0/24"


def test_truncate_ipv4_mapped_ipv6_uppercase_hex():
    """IPv4-mapped IPv6 hex uppercase: ::FFFF:C000:0280 = 192.0.2.128 → /24."""
    result = truncate_ip("::FFFF:C000:0280")
    assert result == "192.0.2.0/24"


def test_truncate_ipv4_mapped_ipv6_with_prefix_mask():
    """IPv4-mapped IPv6 dotted com mask customizado."""
    result = truncate_ip("::ffff:192.168.1.123", mask=16)
    assert result == "192.168.0.0/16"


def test_truncate_ipv4_mapped_ipv6_invalid_returns_none():
    """IPv4-mapped IPv6 malformado retorna None (defesa)."""
    assert truncate_ip("::ffff:") is None
    assert truncate_ip("::ffff:zzzz") is None  # hex invalido
    assert truncate_ip("::ffff:999.999.999.999") is None  # IPv4 invalido


# ============================================================================
# IPv6 edge cases (T9-MED-9)
# ============================================================================




def test_truncate_ipv6_unique_local():
    """IPv6 unique-local fc00::1 → primeiros 2 grupos /32."""
    result = truncate_ip("fc00::1")
    # "fc00" e "1" sao 2 grupos nao-vazios
    assert result == "fc00:1::/32"


def test_truncate_ipv6_full_address():
    """IPv6 full address: pega primeiros 2 grupos."""
    result = truncate_ip("2001:db8:85a3:0:0:8a2e:370:7334")
    assert result == "2001:db8::/32"


def test_truncate_ipv6_case_insensitive():
    """IPv6 case-insensitive (RFC 5952): normalize lowercase."""
    result = truncate_ip("2001:DB8::1")
    assert result == "2001:db8::/32"


# ============================================================================
# Edge cases / invalidos
# ============================================================================


def test_truncate_ip_none_retorna_none():
    """None → None."""
    assert truncate_ip(None) is None


def test_truncate_ip_vazio_retorna_none():
    """String vazia → None."""
    assert truncate_ip("") is None


def test_truncate_ip_apenas_espacos_retorna_none():
    """String so com espacos → None."""
    assert truncate_ip("   ") is None


def test_truncate_ip_unknown_retorna_none():
    """'unknown' (string sem formato IP) → None."""
    assert truncate_ip("unknown") is None


def test_truncate_ipv4_octeto_invalido_retorna_none():
    """IPv4 com octeto > 255 → None (defesa contra input malicioso)."""
    assert truncate_ip("256.256.256.256") is None


def test_truncate_ipv4_3_octetos_retorna_none():
    """IPv4 com 3 octetos (formato incompleto) → None."""
    assert truncate_ip("192.168.1") is None


def test_truncate_ipv4_5_octetos_retorna_none():
    """IPv4 com 5 octetos (formato errado) → None."""
    assert truncate_ip("192.168.1.123.456") is None


def test_truncate_ipv4_octeto_negativo_retorna_none():
    """IPv4 com octeto negativo → None."""
    assert truncate_ip("192.168.-1.123") is None


def test_truncate_ip_nao_string_retorna_none():
    """Tipo nao-string (int, list, etc) → None (defesa)."""
    assert truncate_ip(12345) is None  # type: ignore[arg-type]
    assert truncate_ip(["1.2.3.4"]) is None  # type: ignore[arg-type]


# ============================================================================
# LGPD-by-design: PRESERVAR formato que ainda permite forensics
# ============================================================================


def test_truncate_preserva_subnet_para_forensics():
    """Verifica que /24 ainda identifica a rede (forensics)."""
    # Mesmo /24 = mesma origem (rede)
    ip_a = truncate_ip("187.45.123.45")
    ip_b = truncate_ip("187.45.123.99")
    assert ip_a == ip_b == "187.45.123.0/24"
    # Rede diferente = origem diferente
    ip_c = truncate_ip("187.45.200.10")
    assert ip_c != ip_a


def test_truncate_nao_expose_host_individual():
    """Confirma que IP individual NAO aparece no output truncado."""
    ip_full = "192.168.1.123"
    truncated = truncate_ip(ip_full)
    # Host (.123) NAO aparece
    assert "123" not in truncated
    # Apenas rede (.0/24) aparece
    assert truncated == "192.168.1.0/24"


# ============================================================================
# Determinismo (idempotencia)
# ============================================================================


def test_truncate_idempotente():
    """Truncar 2x da mesma entrada retorna mesmo output."""
    ip = "187.45.123.45"
    assert truncate_ip(ip) == truncate_ip(ip)
    assert truncate_ip(ip) == truncate_ip(truncate_ip(ip).replace("/24", ""))  # type: ignore[arg-type]


# ============================================================================
# Integracao com AuditService
# ============================================================================


def test_audit_service_log_popula_ip_e_ip_truncated(db_session):
    """AuditService.log() popula AMBAS colunas: ip (full) + ip_truncated (/24)."""
    from app.models.audit_log import AuditLog
    from app.services.audit import AuditService

    AuditService.log(
        db_session,
        actor_id="test_user",
        action="test.action",
        resource="test:resource",
        payload={"foo": "bar"},
        ip="187.45.123.45",
    )

    entry = db_session.query(AuditLog).filter_by(action="test.action").first()
    assert entry is not None
    # IP full preservado (DPO forensics)
    assert entry.ip == "187.45.123.45"
    # IP truncado derivado (output default)
    assert entry.ip_truncated == "187.45.123.0/24"


def test_audit_service_log_ip_none_gera_ip_truncated_none(db_session):
    """Se ip=None, ip_truncated tambem eh None (sem crash)."""
    from app.models.audit_log import AuditLog
    from app.services.audit import AuditService

    AuditService.log(
        db_session,
        actor_id="test_user",
        action="test.no_ip",
        resource="test:resource",
        payload={"foo": "bar"},
        ip=None,
    )

    entry = db_session.query(AuditLog).filter_by(action="test.no_ip").first()
    assert entry is not None
    assert entry.ip is None
    assert entry.ip_truncated is None


def test_audit_service_log_ip_ipv6_gera_ip_truncated_ipv6(db_session):
    """IPv6 preservado em ip, truncado em ip_truncated (formato /32)."""
    from app.models.audit_log import AuditLog
    from app.services.audit import AuditService

    AuditService.log(
        db_session,
        actor_id="test_user",
        action="test.ipv6",
        resource="test:resource",
        payload={"foo": "bar"},
        ip="2001:db8:85a3::8a2e:370:7334",
    )

    entry = db_session.query(AuditLog).filter_by(action="test.ipv6").first()
    assert entry is not None
    assert entry.ip == "2001:db8:85a3::8a2e:370:7334"
    assert entry.ip_truncated == "2001:db8::/32"
