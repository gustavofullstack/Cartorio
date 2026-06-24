"""Utility helpers para o app.

Modulos estritamente SEM logica de negocio - apenas funcoes puras
reusaveis (IP truncation, formatacao, parsing).

LGPD-by-design (D5, cartorio-lgpd review 2026-06-24):
- truncate_ip() eh a UNICA fonte da verdade para truncar IP em /24.
- Caller nao deve truncar IP inline — sempre via este helper.
- IP completo continua sendo persistido em audit_log.ip (DPO-only access).
"""
