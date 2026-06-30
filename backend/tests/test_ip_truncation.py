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
