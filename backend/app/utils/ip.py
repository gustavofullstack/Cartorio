"""IP truncation utilities (LGPD art. 5 II + D5).

Decisao arquitetural (cartorio-lgpd cross-review 2026-06-24):
- PRESERVAR IP COMPLETO em audit_log.ip (acesso restrito DPO via /audit/replay)
- TRUNCAR IP em audit_log.ip_truncated (output default, queries normais,
  /metrics/prometheus)

Justificativa LGPD-by-design:
- IP individual eh dado pessoal (LGPD art. 5 II) — difuso mas reconhecido.
- /24 (IPv4) preserva subnet pra forensics (identificar range de attack,
  geo/ASN, ASR) sem tornar IP individual dado titular.
- /32 (IPv6, 1 grupo hex = 16 bits) preserva rede mas mascara host.
- IPv4-mapped IPv6 (::ffff:X.X.X.X): detectado e extraido como IPv4.
- DPO precisa do IP completo em incidente (forensics) — coluna separada
  (audit_log.ip) com acesso restrito.

Helper UNICO: truncate_ip() — qualquer caller que precisar truncar usa aqui.
Evita drift entre logica inline (opencode_go._truncate_ip_to_24 etc).
"""

from __future__ import annotations


def truncate_ip(ip: str | None, mask: int = 24) -> str | None:
    """Trunca IP em /mask (IPv4) ou /32 fixo (IPv6) para uso em output/audit_truncated.

    Args:
        ip: IP em formato texto (IPv4 ou IPv6). Pode ser None ou invalido.
        mask: Tamanho do prefixo para IPv4 (default 24). Apenas multiplos
              de 8 sao suportados (8, 16, 24, 32). Nao-multiplos sao
              arredondados para baixo (defesa). Ignorado para IPv6.

    Returns:
        - IPv4 valido: "192.168.1.0/24" (ultimo octeto zerado + mascara /mask).
        - IPv4-mapped IPv6 (::ffff:1.2.3.4 ou ::ffff:HHHH:HHHH): detecta,
          extrai IPv4, trunca parte v4 (T9-CRIT-3).
        - IPv6 valido: "2001:db8::/32" (2 primeiros grupos + ::/32).
        - IP invalido ou None: None (caller trata como 'unknown').

    Examples:
        >>> truncate_ip("192.168.1.123")
        '192.168.1.0/24'
        >>> truncate_ip("::ffff:192.168.1.123")  # IPv4-mapped IPv6
        '192.168.1.0/24'
        >>> truncate_ip("::ffff:c000:0280")  # IPv4-mapped IPv6 hex
        '192.0.2.128/24'
        >>> truncate_ip("fe80::1")  # IPv6 link-local
        'fe80:1::/32'
        >>> truncate_ip("2001:db8::1")
        '2001:db8::/32'
        >>> truncate_ip("::1")  # IPv6 loopback (1 grupo)
        '0:1::/32'
        >>> truncate_ip("unknown")
        None
        >>> truncate_ip(None)
        None

    LGPD: use em campos de OUTPUT. Para preservar IP completo com acesso
    restrito (DPO forensics), use audit_log.ip sem truncar.
    """
    if not ip or not isinstance(ip, str):
        return None

    # T9-MED-9: lower() para case-insensitive (RFC 5952).
    ip = ip.strip().lower()
    if not ip:
        return None

    # IPv4-mapped IPv6 (T9-CRIT-3): ::ffff:X.X.X.X ou ::ffff:HHHH:HHHH (hex)
    # Detecta prefixo IPv4-mapped, extrai parte v4, trunca como IPv4.
    if ip.startswith("::ffff:"):
        v4_part = ip[7:]  # remove "::ffff:"
        # Tenta como IPv4 dotted (ex: ::ffff:192.168.1.1)
        if "." in v4_part:
            return truncate_ip(v4_part, mask)
        # Hex form (ex: ::ffff:c000:0280 = 192.0.2.128)
        try:
            if ":" in v4_part:
                hex_parts = v4_part.split(":")
                if len(hex_parts) == 2 and all(
                    len(p) == 4 and all(c in "0123456789abcdef" for c in p) for p in hex_parts
                ):
                    hi = int(hex_parts[0], 16)
                    lo = int(hex_parts[1], 16)
                    ipv4 = f"{(hi >> 8) & 0xFF}.{hi & 0xFF}.{(lo >> 8) & 0xFF}.{lo & 0xFF}"
                    return truncate_ip(ipv4, mask)
        except (ValueError, IndexError):
            pass
        # Se nao conseguiu extrair IPv4 do mapeado, retorna None (defesa)
        return None

    # IPv4 (4 grupos decimais separados por .)
    if "." in ip and ":" not in ip:
        parts = ip.split(".")
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            # mask deve estar em [8, 32] E multiplo de 8. Caso contrario,
            # arredonda para o multiplo de 8 mais proximo abaixo (defesa).
            if mask < 8:
                mask = 8
            elif mask > 32:
                mask = 32
            mask = (mask // 8) * 8
            if mask == 0:
                mask = 8
            octets_to_keep = mask // 8
            kept = ".".join(parts[:octets_to_keep])
            zeros_needed = 4 - octets_to_keep
            return f"{kept}{'.0' * zeros_needed}/{mask}"
        return None

    # IPv6 (grupos hexadecimais separados por :) — sempre /32 (LGPD-by-design)
    if ":" in ip:
        groups = ip.split(":")
        non_empty = [g for g in groups if g]
        if len(non_empty) >= 2:
            return f"{non_empty[0]}:{non_empty[1]}::/32"
        # Se so 1 grupo nao-vazio (ex: ::1, fe80::), retorna com zeros
        if len(non_empty) == 1:
            return f"{non_empty[0]}:0::/32"
        return None

    return None
