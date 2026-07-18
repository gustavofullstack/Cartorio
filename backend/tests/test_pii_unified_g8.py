"""G8.12.T1 — Regression tests do PII masking unificado.

Cada teste falha se o helper regredir (LGPD art. 46: zero raw PII em
output). Cobre:

- ``mask(kind, value)`` full vs partial
- Determinismo do output
- Edge cases: CPF formatado/nao-formatado/None/vazio/parcial
- Re-export do scrub canonico (sem divergencia)
- Re-export do hash_pii (LGPD-by-design salt)
- Re-export do detect_only + has_raw_pii
- mcp_output_has_raw_cpf usa o pattern canonico (sem duplicar regex)
- No-leak: nenhum CPF sample deve aparecer raw em output
- validate_cns / validate_cnh re-exports preservam semantica

LGPD by design: o teste ``test_unified_no_raw_leak`` eh o mais
importante. Roda com 6 CPFs reais (incluindo validos) e exige que
NENHUM apareca no output de ``mask(...)``.

Modified by Gustavo Almeida + cartorio-dev (G8 Wave 44 — 2026-07-18).
"""

from __future__ import annotations

import warnings

import pytest

from app.services.pii import (
    ScrubResult as _ScrubResult,
    validate_cnh as _validate_cnh,
    validate_cns as _validate_cns,
)
from app.services.pii_unified import (
    PiiKind,
    _CPF_PATTERN,
    deprecation_notice,
    detect_only,
    has_raw_pii,
    hash_pii,
    mask,
    mask_nome,
    mask_safe,
    scrub,
)


# CPFs com DV valido (Receita Federal). 123.456.789-09 NAO eh valido.
VALID_CPFS = (
    "529.982.247-25",
    "52998224725",
    "111.444.777-35",
)


# CPFs com DV INVALIDO — usados para testar que DETECCAO funciona mesmo
# se o DV falhar (regex detecta estrutura, nao valida DV).
INVALID_CPFS = (
    "123.456.789-00",
    "111.111.111-11",
    "987.654.321-99",
)


SAMPLE_CPFS_FOR_LEAK = (
    "529.982.247-25",
    "111.444.777-35",
    "52998224725",
    "123.456.789-00",
    "111.111.111-11",
    "987.654.321-99",
)


class TestUnifiedMaskFull:
    """``mask(kind, value)`` com partial=False: LGPD-by-design full redaction."""

    def test_mask_cpf_formatado_full(self) -> None:
        """CPF formatado -> [CPF_REDACTED]."""
        out = mask("cpf", "529.982.247-25")
        assert "529.982.247-25" not in out
        assert "[CPF_REDACTED]" in out

    def test_mask_cpf_sem_formatacao_full(self) -> None:
        """CPF sem pontuacao (11 digits) -> [CPF_REDACTED]."""
        out = mask("cpf", "52998224725")
        assert "52998224725" not in out
        assert "[CPF_REDACTED]" in out

    def test_mask_cnpj_full(self) -> None:
        """CNPJ formatado -> [CNPJ_REDACTED]."""
        out = mask("cnpj", "11.222.333/0001-81")
        assert "11.222.333" not in out
        assert "[CNPJ_REDACTED]" in out

    def test_mask_email_full(self) -> None:
        """Email -> [EMAIL_REDACTED]."""
        out = mask("email", "fulano@example.com")
        assert "fulano" not in out
        assert "@example.com" not in out
        assert "[EMAIL_REDACTED]" in out

    def test_mask_auto_uses_scrub(self) -> None:
        """kind='auto' delega para ``scrub()`` (13 patterns)."""
        text = "Cliente CPF 529.982.247-25 tel (11) 98765-4321 email a@b.com"
        out = mask("auto", text)
        assert "529.982.247-25" not in out
        assert "98765-4321" not in out
        assert "a@b.com" not in out


class TestUnifiedMaskPartial:
    """``mask(kind, value, partial=True)`` estilo log display (***789-00)."""

    def test_mask_cpf_partial(self) -> None:
        """CPF partial -> ***789-00 (LGPD display-safe)."""
        out = mask("cpf", "123.456.789-00", partial=True)
        assert "***789-00" == out
        assert "123.456.789-00" not in out

    def test_mask_cpf_sem_formato_partial(self) -> None:
        """CPF sem formato -> partial reveal do final."""
        out = mask("cpf", "12345678900", partial=True)
        # Regex do pii_sanitizer so pega formato XXX.XXX.XXX-XX.
        # Sem formatacao, passa direto. Isso eh by design (ver docstring).
        # Apenas garante que NAO ha raw visible.
        assert "12345678" not in out or "***" in out

    def test_mask_email_partial_domain(self) -> None:
        """Email partial -> ***@dominio (preserva dominio para triage)."""
        out = mask("email", "gustavo@gmail.com", partial=True)
        assert "@gmail.com" in out
        assert "gustavo" not in out
        assert "***" in out

    def test_mask_cnpj_partial(self) -> None:
        """CNPJ partial -> ***/0001-90 (preserva sufixo)."""
        out = mask("cnpj", "12.345.678/0001-90", partial=True)
        assert "/0001-90" in out
        assert "12.345.678" not in out

    def test_mask_phone_partial_br(self) -> None:
        """Phone BR partial -> ***4321 (ultimos 4)."""
        out = mask("phone", "(11) 98765-4321", partial=True)
        assert "4321" in out
        assert "***" in out
        assert "98765" not in out


class TestUnifiedEdgeCases:
    """Edge cases: None / vazio / whitespace / kind invalido."""

    def test_mask_none_returns_empty_string(self) -> None:
        """``None`` retorna ``""`` (sem excecao)."""
        assert mask("cpf", None) == ""

    def test_mask_empty_string_returns_empty(self) -> None:
        """String vazia retorna ``""``."""
        assert mask("cpf", "") == ""

    def test_mask_whitespace_only_returns_empty(self) -> None:
        """Whitespace-only retorna ``""`` (LGPD: nao processa ruido)."""
        assert mask("cpf", "   ") == ""

    def test_mask_trims_whitespace(self) -> None:
        """Whitespace nas pontas eh stripped antes do scrub."""
        out = mask("cpf", "  529.982.247-25  ")
        assert "529.982.247-25" not in out

    def test_mask_safe_shortcut_auto(self) -> None:
        """``mask_safe`` == ``mask('auto', ...)``."""
        text = "doc cpf 529.982.247-25"
        assert mask_safe(text) == mask("auto", text)


class TestUnifiedNoLeak:
    """LGPD Art. 46 — regressao que falha se QUALQUER CPF raw escapar."""

    @pytest.mark.parametrize("cpf", SAMPLE_CPFS_FOR_LEAK)
    def test_unified_no_raw_leak_partial(self, cpf: str) -> None:
        """Nenhum CPF sample pode aparecer raw em ``partial=True`` output."""
        out = mask("cpf", cpf, partial=True)
        # O CPF sem formatacao (apenas digits) pode coincidir com output
        # de partial se for exatamente '***' + suffix. Conferimos:
        # - o valor EXATO deve NAO aparecer
        if "." in cpf or "-" in cpf:
            assert cpf not in out, (
                f"Leak: partial mask devolveu o CPF raw {cpf!r} em {out!r}"
            )
        # digits sem formatacao: "12345678" nunca pode aparecer isolado
        digits_only = "".join(ch for ch in cpf if ch.isdigit())
        assert digits_only not in out, (
            f"Leak digits-only {digits_only!r} em partial output {out!r}"
        )

    @pytest.mark.parametrize("cpf", SAMPLE_CPFS_FOR_LEAK)
    def test_unified_no_raw_leak_full(self, cpf: str) -> None:
        """Nenhum CPF sample pode aparecer raw em ``partial=False`` output."""
        out = mask("cpf", cpf)
        assert cpf not in out
        digits_only = "".join(ch for ch in cpf if ch.isdigit())
        assert digits_only not in out, (
            f"Leak digits-only {digits_only!r} em full output {out!r}"
        )

    def test_unified_phone_partial_no_leak(self) -> None:
        """Phone BR partial NAO pode devolver DDD+9digitos raw."""
        out = mask("phone", "(11) 98765-4321", partial=True)
        assert "98765" not in out
        # Ultimos 4 podem aparecer por design (reveal-last-4).

    def test_unified_no_leak_mixed_text(self) -> None:
        """Texto com MULTIPLOS CPFs nao vaza nenhum."""
        text = (
            "Notas: cliente 529.982.247-25 e conjuge 111.444.777-35."
            " Ambos assinaram em 2026-07-18."
        )
        out = mask("auto", text)
        assert "529.982.247-25" not in out
        assert "111.444.777-35" not in out


class TestUnifiedDeterminism:
    """Output deve ser determinístico (LGPD chain + audit reproducibility)."""

    def test_mask_cpf_deterministic(self) -> None:
        """Mesma input -> mesmo output (sem randomness)."""
        for _ in range(5):
            assert mask("cpf", "529.982.247-25") == "[CPF_REDACTED]"

    def test_hash_pii_deterministic(self) -> None:
        """``hash_pii`` eh determinístico com mesmo salt."""
        a = hash_pii("529.982.247-25", "salt-2026")
        b = hash_pii("529.982.247-25", "salt-2026")
        assert a == b
        assert len(a) == 64  # SHA-256 hex

    def test_hash_pii_salt_changes_output(self) -> None:
        """Salts diferentes -> outputs diferentes (anti-rainbow)."""
        a = hash_pii("529.982.247-25", "salt-A")
        b = hash_pii("529.982.247-25", "salt-B")
        assert a != b

    def test_hash_pii_no_empty_fallback(self) -> None:
        """``hash_pii`` nao retorna string vazia em caso de sucesso."""
        assert hash_pii("qualquer-input", "qualquer-salt") != ""


class TestUnifiedReExports:
    """Re-exports preservam identidade e semantica (zero regressao)."""

    def test_scrub_reexport_returns_same_scrub_result(self) -> None:
        """``scrub`` re-exportado produz o MESMO resultado que o canonico."""
        from app.services.pii import scrub as canonical_scrub

        text = "Cliente CPF 529.982.247-25"
        a = scrub(text)
        b = canonical_scrub(text)
        assert a.text == b.text
        assert a.findings == b.findings
        assert a.redaction_count == b.redaction_count

    def test_scrub_result_is_canonical_type(self) -> None:
        """``ScrubResult`` retornado eh o tipo canonico (mesma classe)."""
        result = scrub("cpf 529.982.247-25")
        assert isinstance(result, _ScrubResult)

    def test_detect_only_reexport(self) -> None:
        """``detect_only`` re-exportado funciona identicamente."""
        findings = detect_only("cpf 529.982.247-25 email a@b.com")
        assert "cpf" in findings
        assert "email" in findings

    def test_has_raw_pii_shortcut(self) -> None:
        """``has_raw_pii`` eh shortcut idiomatic para ``bool(detect_only)``."""
        assert has_raw_pii("texto sem PII") is False
        assert has_raw_pii("cpf 529.982.247-25") is True

    def test_validate_cns_reexport(self) -> None:
        """``validate_cns`` preserva semantica (16 digits only)."""
        valid_16 = "1234567890123456"  # hipotetico
        # DV arbitrario pode estar errado; so importa o tipo de retorno
        result = _validate_cns(valid_16)
        assert isinstance(result, bool)
        # CNS de 15 digits NAO eh confiavel
        assert _validate_cns("123456789012345") is False

    def test_validate_cnh_reexport(self) -> None:
        """``validate_cnh`` preserva semantica (11 digits only)."""
        result = _validate_cnh("12345678901")
        assert isinstance(result, bool)
        # CNH de 9 digits NAO eh confiavel
        assert _validate_cnh("123456789") is False

    def test_mask_nome_delegates_to_crypto(self) -> None:
        """``mask_nome`` delega para ``app.services.crypto.mask_nome``."""
        assert mask_nome("Gustavo Almeida") == "G*** A***"
        assert mask_nome(None) == "[nome indisponivel]"


class TestUnifiedMcpPattern:
    """Garante que ``mcp_pii`` reusa o regex canonico (DRY)."""

    def test_cpf_pattern_matches_canonical(self) -> None:
        """``_CPF_PATTERN`` eh o compiled regex de ``pii._PATTERNS['cpf']``."""
        from app.services.pii import _PATTERNS

        assert _CPF_PATTERN is _PATTERNS["cpf"]
        assert _CPF_PATTERN.pattern == r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"

    def test_cpf_pattern_matches_valid_cpf(self) -> None:
        """Pattern canonico matcheia CPFs validos E invalidos (LGPD defesa)."""
        for cpf in VALID_CPFS:
            assert _CPF_PATTERN.search(cpf), f"CPF {cpf} nao matcheou"

    def test_mcp_output_has_raw_cpf_uses_canonical(self) -> None:
        """``mcp_output_has_raw_cpf`` reusa pattern canonico (no-dup)."""
        from app.services.mcp_pii import mcp_output_has_raw_cpf

        # Raw detection funciona
        assert mcp_output_has_raw_cpf("cpf 529.982.247-25") is True
        # REDACTED markers NAO sao leak
        assert mcp_output_has_raw_cpf("cpf [CPF_REDACTED]") is False
        # Empty / safe
        assert mcp_output_has_raw_cpf("texto sem pii") is False


class TestUnifiedDeprecationNotice:
    """Hook de migracao para futuras deprecations."""

    def test_deprecation_notice_emits_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            deprecation_notice("app.utils.pii_sanitizer")
        assert any(
            issubclass(w.category, DeprecationWarning) and "pii_unified" in str(w.message)
            for w in caught
        )


class TestUnifiedPiiKindLiteral:
    """``PiiKind`` eh o Literal type guardado pelo type-checker."""

    def test_pii_kind_accepts_valid_kinds(self) -> None:
        """Type-check passa para os kinds canonicos."""
        # Apenas exercita o tipo (mypy faria a checagem em strict mode).
        valid: PiiKind = "cpf"
        assert valid == "cpf"

    def test_mask_calls_with_each_kind(self) -> None:
        """Cada kind suportado produz string sem excecao."""
        for kind in ("cpf", "cnpj", "rg", "email", "phone", "auto"):
            out = mask(kind, "529.982.247-25")  # type: ignore[arg-type]
            assert isinstance(out, str)


# ============================================================================
# Compat: garantir que pii_sanitizer.sanitize_rg NAO esta REGREDINDO.
# Issue conhecido (G8.12.T1 follow-up): o regex \b(?:([A-Z]{2})-)?(\d{6,10})\b
# NAO pega RG com pontos (ex: "MG-12.345.678" passa direto). Esta tarefa
# apenas documenta — a correcao do regex eh uma task separada, fora do
# escopo do DRY (mudaria semantica de pii_sanitizer pre-existente).
# ============================================================================


class TestPiiSanitizerRgKnownGap:
    """Documenta gap atual sem corrigir (escopo DRY apenas)."""

    def test_sanitize_rg_with_dots_unchanged_documented_gap(self) -> None:
        """RG com pontos NAO eh mascarado pelo sanitize_rg (gap conhecido)."""
        from app.utils.pii_sanitizer import sanitize_rg

        # DOC ONLY: este teste falha se o gap for corrigido por acidente.
        # Quando corrigir (futura task), substituir o `assert ==` por
        # `assert !=` e adicionar caso nominal.
        assert sanitize_rg("MG-12.345.678") == "MG-12.345.678"
