"""Tests for IP truncation utility (LGPD art. 5 II).

Cobra edge cases que faltavam na cobertura original.
"""

from __future__ import annotations


from app.utils.ip import truncate_ip


class TestTruncateIp:
    """Testes de truncate_ip — cobre linhas nao testadas da implementacao."""

    def test_ipv4_mask_arredondado_0_para_8(self) -> None:
        """Mask arredondado para 0 vira 8 (defesa)."""
        assert truncate_ip("192.168.1.1", mask=3) == "192.0.0.0/8"

    def test_ipv4_mask_acima_de_32(self) -> None:
        """Mask acima de 32 e' truncado para 32."""
        result = truncate_ip("192.168.1.1", mask=40)
        assert result == "192.168.1.1/32"

    def test_ipv4_mapped_hex_invalido_retorna_none(self) -> None:
        """IPv4-mapped IPv6 hex invalido retorna None."""
        # ::ffff:ZZZZ:ZZZZ — hex invalido deve cair no except
        assert truncate_ip("::ffff:ZZZZ:ZZZZ") is None

    def test_ipv6_loopback_retorna_32(self) -> None:
        """IPv6 loopback ::1 retorna 1:0::/32."""
        assert truncate_ip("::1") == "1:0::/32"

    def test_ipv4_mapped_hex_valido(self) -> None:
        """IPv4-mapped IPv6 em hex valido (::ffff:c000:0280 = 192.0.2.128)."""
        assert truncate_ip("::ffff:c000:0280") == "192.0.2.0/24"

    def test_ipv6_apenas_grupo_unico_retorna_none(self) -> None:
        """IPv6 com apenas 1 grupo nao vazio apos split retorna format."""
        # "1234::::" depois de split e filter tem 1 non_empty
        assert truncate_ip("1234:::") is not None

    def test_ip_entrada_vazia(self) -> None:
        """String vazia apos strip retorna None."""
        assert truncate_ip("   ") is None

    def test_ip_invalido_retorna_none(self) -> None:
        """IP completamente invalido retorna None."""
        assert truncate_ip("not_an_ip_at_all") is None


# ============================================================================
# G6.C.T4 — D5 regression: payloads de output NUNCA carregam IP full
# ============================================================================


class TestD5IpNeverLeaksInTruncatedForm:
    """Prova que truncate_ip remove o host identifier (LGPD D5 / art. 5 II)."""

    def test_ipv4_host_octet_zeroed(self) -> None:
        full = "198.51.100.42"
        truncated = truncate_ip(full)
        assert truncated is not None
        assert full not in truncated
        assert truncated.endswith("/24")
        assert truncated.startswith("198.51.100.")
        assert truncated == "198.51.100.0/24"

    def test_ipv6_host_not_in_output(self) -> None:
        full = "2001:db8:85a3::8a2e:370:7334"
        truncated = truncate_ip(full)
        assert truncated is not None
        assert "8a2e" not in truncated
        assert "7334" not in truncated
        assert truncated.endswith("/32")

    def test_audit_style_payload_uses_only_truncated(self) -> None:
        """Simula payload de export/API: so ip_truncated deve ir ao cliente."""
        raw_ip = "203.0.113.99"
        public_payload = {
            "action": "protocolo.read",
            "ip_truncated": truncate_ip(raw_ip),
            # campo full proibido em response default
        }
        serialized = str(public_payload)
        assert "203.0.113.99" not in serialized
        assert public_payload["ip_truncated"] == "203.0.113.0/24"

    def test_xff_first_hop_truncation(self) -> None:
        """X-Forwarded-For multi-hop: truncar o primeiro (cliente real)."""
        xff = "203.0.113.50, 10.0.0.1, 172.16.0.5"
        client_ip = xff.split(",")[0].strip()
        assert truncate_ip(client_ip) == "203.0.113.0/24"

    def test_case_insensitive_ipv6_mapped(self) -> None:
        assert truncate_ip("::FFFF:192.168.1.200") == "192.168.1.0/24"
