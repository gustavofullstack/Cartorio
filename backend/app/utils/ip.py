"""IP truncation utilities (LGPD art. 5 II + D5).

Decisao arquitetural (cartorio-lgpd cross-review 2026-06-24):
- PRESERVAR IP COMPLETO em audit_log.ip (acesso restrito DPO via /audit/replay)
- TRUNCAR IP em audit_log.ip_truncated (output default, exposto em queries
  normais e metricas /metrics/prometheus)

Justificativa LGPD-by-design:
- IP individual eh dado pessoal (LGPD art. 5 II) — difuso mas reconhecido.
- /24 (IPv4) preserva subnet pra forensics (identificar range de attack,
  geo/ASN, ASR) sem tornar IP individual dado titular.
- /32 (IPv6, 1 grupo hex = 16 bits) preserva rede mas mascara host.
- DPO precisa do IP completo em incidente (forensics) — por isso coluna
  separada (audit_log.ip) com acesso restrito.

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
        - IPv4 valido: "192.168.1.0/24" (octetos truncados + mascara /mask).
        - IPv6 valido: "2001:db8::/32" (2 primeiros grupos + ::/32).
        - IP invalido ou None: None (caller trata como 'unknown').

    Examples:
        >>> truncate_ip("192.168.1.123")
        '192.168.1.0/24'
        >>> truncate_ip("10.0.0.1", mask=16)
        '10.0.0.0/16'
        >>> truncate_ip("2001:db8::1")
        '2001:db8::/32'
        >>> truncate_ip("unknown")
        None
        >>> truncate_ip(None)
        None
        >>> truncate_ip("")
        None

    LGPD: use em campos de OUTPUT. Para preservar IP completo com acesso
    restrito (DPO forensics), use audit_log.ip sem truncar.
    """
    if not ip or not isinstance(ip, str):
        return None

    ip = ip.strip()
    if not ip:
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
            # Arredonda para multiplo de 8 abaixo
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
        return None

    return None
