"""Testes para check_no_literal_keys.py (G8.14.T3 — LGPD Art. 46).

Wave 48 — CI secrets scanning avancado.
Cada test exercita UM pattern ou propriedade do scanner.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Adiciona scripts/ ao path (script tem if __name__ == '__main__' entao e seguro importar).
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import check_no_literal_keys as cnlk  # noqa: E402


# ============================================================================
# Fixtures / helpers.
# ============================================================================
@pytest.fixture
def fake_keys_file(tmp_path: Path) -> Path:
    """Cria arquivo com 1 key por pattern — usado pra deteccao."""
    f = tmp_path / "fake_keys.py"
    f.write_text(
        '"""Fixture com TODOS os patterns — deve disparar TODOS."""\n'
        'OPENAI = "sk-proj-FAKE1234567890abcdefghij"\n'
        'ANTHROPIC = "sk-ant-api03-FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
        'AWS = "AKIAIOSFODNN7EXAMPLE"\n'
        'AWS_TEMP = "ASIAIOSFODNN7EXAMPLE"\n'
        'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
        'TELEGRAM = "1234567890:AAEhBOweik6ad9JQFmR8bFH_qqKjV8sFAKE"\n'
        'SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.fake"\n'
        'MINIMAX = "sk-cp-FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
        'SLACK = "xoxb-1234567890123-1234567890123-FAKEFAKEFAKEFAKEFAKE"\n'
        'LINEAR = "lin_api_FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n'
        'AUTH = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.fake_sig_here"\n'
        'PKCS8 = "-----BEGIN PRIVATE KEY-----\\nFAKE\\n-----END PRIVATE KEY-----"\n',
        encoding="utf-8",
    )
    return f


@pytest.fixture
def clean_file(tmp_path: Path) -> Path:
    """Arquivo SEM chaves — apenas hashes hex, docstrings, variaveis normais."""
    f = tmp_path / "clean.py"
    f.write_text(
        '"""Clean code — NAO deve disparar nenhum pattern."""\n'
        "import hashlib\n"
        "import os\n"
        "\n"
        "# SHA256 (64 hex) — IGNORAR\n"
        'HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"\n'
        "\n"
        "# UUID v4 — IGNORAR\n"
        'UUID = "550e8400-e29b-41d4-a716-446655440000"\n'
        "\n"
        "# Variavel parece key mas sem prefixo provider\n"
        'random_token = "abcdef1234567890abcdef1234567890"\n'
        "\n"
        '# Comentario descrevendo "sk-" minusculo\n'
        "# docs: use sk- prefix for internal services\n",
        encoding="utf-8",
    )
    return f


@pytest.fixture
def optout_file(tmp_path: Path) -> Path:
    """Linha com # noqa: ALLOW_KEY_FALLBACK — DEVE ser ignorada."""
    f = tmp_path / "optout.py"
    f.write_text(
        'KEY = "lin_api_FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # noqa: ALLOW_KEY_FALLBACK (motivo: test fixture)\n',
        encoding="utf-8",
    )
    return f


# ============================================================================
# Pattern detection (1 test por pattern principal — 9+ tests).
# ============================================================================
class TestPatternDetection:
    """Cada pattern CRITICAL/HIGH deve ser detectado."""

    def test_detects_lin_api(self, tmp_path: Path) -> None:
        """Linear API key (provider-prefixed HIGH)."""
        f = tmp_path / "x.py"
        f.write_text('X = "lin_api_FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n', encoding="utf-8")
        v = cnlk.scan_file(f)
        assert any(r.rule == "PROVIDER_LITERAL_GENERIC" for r in v)
        assert any(r.severity == "high" for r in v)

    def test_detects_sk_openai_project(self, tmp_path: Path) -> None:
        """OpenAI project-scoped key (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text('X = "sk-proj-FAKE1234567890abcdefghij"\n', encoding="utf-8")
        v = cnlk.scan_file(f)
        assert any(r.rule == "OPENAI_PROJECT_KEY" and r.severity == "critical" for r in v)

    def test_detects_sk_anthropic(self, tmp_path: Path) -> None:
        """Anthropic key (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text(
            'X = "sk-ant-api03-FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n',
            encoding="utf-8",
        )
        v = cnlk.scan_file(f)
        assert any(r.rule == "ANTHROPIC_KEY" and r.severity == "critical" for r in v)

    def test_detects_aws_access_key(self, tmp_path: Path) -> None:
        """AWS access key (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text('AWS = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
        v = cnlk.scan_file(f)
        assert any(r.rule == "AWS_ACCESS_KEY_ID" and r.severity == "critical" for r in v)

    def test_detects_telegram_bot_token(self, tmp_path: Path) -> None:
        """Telegram bot token (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text('TG = "1234567890:AAEhBOweik6ad9JQFmR8bFH_qqKjV8sFAKE"\n', encoding="utf-8")
        v = cnlk.scan_file(f)
        assert any(r.rule == "TELEGRAM_BOT_TOKEN" and r.severity == "critical" for r in v)

    def test_detects_pkcs8_private_key(self, tmp_path: Path) -> None:
        """PKCS8 private key block (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text(
            'PKCS8 = """-----BEGIN PRIVATE KEY-----\\nFAKE_BODY\\n-----END PRIVATE KEY-----"""\n',
            encoding="utf-8",
        )
        v = cnlk.scan_file(f)
        assert any(r.rule == "PKCS8_PRIVATE_KEY" and r.severity == "critical" for r in v)

    def test_detects_supabase_jwt(self, tmp_path: Path) -> None:
        """Supabase / generic JWT (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text(
            'TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.fake_sig"\n',
            encoding="utf-8",
        )
        v = cnlk.scan_file(f)
        assert any(r.rule == "SUPABASE_SERVICE_ROLE_JWT" and r.severity == "critical" for r in v)

    def test_detects_minimax_cp_key(self, tmp_path: Path) -> None:
        """MiniMax Coding Plan key (CRITICAL)."""
        f = tmp_path / "x.py"
        f.write_text(
            'MINIMAX = "sk-cp-FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n', encoding="utf-8"
        )
        v = cnlk.scan_file(f)
        assert any(r.rule == "MINIMAX_KEY" and r.severity == "critical" for r in v)

    def test_detects_env_fallback_pattern(self, tmp_path: Path) -> None:
        """os.environ.get(KEY, 'literal_fallback') (MEDIUM)."""
        f = tmp_path / "x.py"
        f.write_text(
            'import os\nKEY = os.environ.get("MY_KEY", "FAKE_FALLBACK_VALUE_xxxxxxxxxxxx")\n',
            encoding="utf-8",
        )
        v = cnlk.scan_file(f)
        assert any(r.rule == "ENV_FALLBACK" for r in v)


# ============================================================================
# False-positive guards (NÃO deve disparar).
# ============================================================================
class TestNoFalsePositives:
    """Garantias contra FPs comuns."""

    def test_no_false_positive_on_sha256_hash(self, clean_file: Path) -> None:
        """SHA256 hex (64 chars) NAO trigga pattern algum."""
        v = cnlk.scan_file(clean_file)
        assert v == [], f"FP em hash hex: {v}"

    def test_no_false_positive_on_uuid(self, clean_file: Path) -> None:
        """UUID v4 NAO trigga."""
        v = cnlk.scan_file(clean_file)
        assert not any(r.rule == "SUPABASE_SERVICE_ROLE_JWT" for r in v)

    def test_no_false_positive_on_lowercase_sk_in_comment(self, clean_file: Path) -> None:
        """`sk-` lowercase em comentario NAO trigga (case-sensitive)."""
        v = cnlk.scan_file(clean_file)
        assert not any("ANTHROPIC" in r.rule or "OPENAI" in r.rule for r in v)

    def test_env_example_allowed(self, tmp_path: Path) -> None:
        """`.env.example` com placeholder e SKIPPED (na whitelist)."""
        env = tmp_path / ".env.example"
        env.write_text("LITELLM_API_KEY=sk-litellm-DEACTIVATED-2026-06\n", encoding="utf-8")
        v = cnlk.scan_file(env)
        assert v == [], f".env.example deveria ser skipado: {v}"


# ============================================================================
# Opt-out mechanisms.
# ============================================================================
class TestOptOut:
    """Verifica mecanismos de whitelisting."""

    def test_inline_noqa_marker(self, optout_file: Path) -> None:
        """`# noqa: ALLOW_KEY_FALLBACK` na linha IGNORA a violacao."""
        v = cnlk.scan_file(optout_file)
        assert v == [], f"opt-out marker deveria ignorar: {v}"

    def test_baseline_file_whitelists_fingerprint(self, tmp_path: Path) -> None:
        """Fingerprint em .baseline e EXCLUIDO das violacoes."""
        f = tmp_path / "f.py"
        f.write_text('KEY = "lin_api_FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n', encoding="utf-8")
        baseline = tmp_path / ".baseline"
        baseline.write_text(f"{f.name}:1:PROVIDER_LITERAL_GENERIC\n", encoding="utf-8")
        baseline_set = cnlk.load_baseline(baseline)
        v = cnlk.scan_file(f)
        rel = f.name  # simplified
        filtered = [r for r in v if r.fingerprint(rel) not in baseline_set]
        assert filtered == []


# ============================================================================
# Severity / threshold logic.
# ============================================================================
class TestSeverity:
    """Filtragem por severity."""

    def test_severity_critical_filters_out_low(self, fake_keys_file: Path) -> None:
        """severity=critical EXCLUI HIGH/MEDIUM/LOW."""
        all_v = cnlk.scan_file(fake_keys_file)
        critical_only = cnlk.filter_by_severity(all_v, cnlk.SEVERITY_CRITICAL)
        for v in critical_only:
            assert v.severity == "critical"

    def test_severity_low_includes_all(self, fake_keys_file: Path) -> None:
        """severity=low inclui TUDO."""
        all_v = cnlk.scan_file(fake_keys_file)
        low = cnlk.filter_by_severity(all_v, cnlk.SEVERITY_LOW)
        assert len(low) == len(all_v)

    def test_severity_rank_ordering(self) -> None:
        """critical > high > medium > low (ranking)."""
        assert cnlk.SEVERITY_RANK["critical"] > cnlk.SEVERITY_RANK["high"]
        assert cnlk.SEVERITY_RANK["high"] > cnlk.SEVERITY_RANK["medium"]
        assert cnlk.SEVERITY_RANK["medium"] > cnlk.SEVERITY_RANK["low"]


def test_cli_redacts_detected_value_from_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failing scanner must identify the location without leaking the matched value."""
    secret_like_value = "sk-proj-FAKE1234567890abcdefghij"
    source = tmp_path / "unsafe.py"
    source.write_text(f'KEY = "{secret_like_value}"\n', encoding="utf-8")

    rc = cnlk.main(["--root", str(tmp_path), "--severity", "critical"])

    output = capsys.readouterr().out
    assert rc == 1
    assert "unsafe.py:1 [CRITICAL][OPENAI_PROJECT_KEY]" in output
    assert "[valor redigido]" in output
    assert secret_like_value not in output


# ============================================================================
# Skip / vendor dirs.
# ============================================================================
class TestSkipRules:
    """Diretorias de vendor sao ignoradas."""

    def test_vendor_dir_skipped(self, tmp_path: Path) -> None:
        """Arquivos em .venv/ NAO sao escaneados."""
        vendor = tmp_path / ".venv" / "site-packages"
        vendor.mkdir(parents=True)
        leaked = vendor / "leaked.py"
        leaked.write_text('KEY = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
        results = list(cnlk.iter_python_files([tmp_path]))
        assert leaked not in results
        assert all(".venv" not in str(p) for p in results)

    def test_venv312_skipped(self, tmp_path: Path) -> None:
        """.venv312 (atual) tambem e skipado."""
        vendor = tmp_path / ".venv312" / "lib"
        vendor.mkdir(parents=True)
        leaked = vendor / "leaked.py"
        leaked.write_text('KEY = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
        results = list(cnlk.iter_python_files([tmp_path]))
        assert leaked not in results

    def test_self_file_skipped(self, tmp_path: Path) -> None:
        """check_no_literal_keys.py NAO se auto-escaneia."""
        fake_self = tmp_path / "check_no_literal_keys.py"
        fake_self.write_text(
            'X = "AKIAIOSFODNN7EXAMPLE"\n',  # seria detectado se escaneasse
            encoding="utf-8",
        )
        results = list(cnlk.iter_python_files([tmp_path]))
        assert fake_self not in results


# ============================================================================
# Integration: main() exit codes.
# ============================================================================
class TestMainExitCode:
    """Validacao end-to-end do entrypoint."""

    def test_clean_dir_exits_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """main() retorna 0 quando dir esta clean."""
        clean = tmp_path / "clean.py"
        clean.write_text("X = 1\n", encoding="utf-8")
        # Substitui ROOT defaults por tmp_path.
        monkeypatch.setattr(cnlk, "BACKEND_DIR", tmp_path)
        rc = cnlk.main(["--root", str(tmp_path)])
        assert rc == 0

    def test_dir_with_key_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() retorna 1 quando acha chave."""
        bad = tmp_path / "bad.py"
        bad.write_text('X = "sk-proj-FAKE1234567890abcdefghij"\n', encoding="utf-8")
        monkeypatch.setattr(cnlk, "BACKEND_DIR", tmp_path)
        rc = cnlk.main(["--root", str(tmp_path), "--severity", "critical"])
        assert rc == 1

    def test_report_only_exits_zero_even_with_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--report-only sempre exit 0 (dry-run)."""
        bad = tmp_path / "bad.py"
        bad.write_text('X = "sk-proj-FAKE1234567890abcdefghij"\n', encoding="utf-8")
        monkeypatch.setattr(cnlk, "BACKEND_DIR", tmp_path)
        rc = cnlk.main(["--root", str(tmp_path), "--report-only"])
        assert rc == 0

    def test_severity_critical_masks_lower_severity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """severity=critical + so HIGH/MEDIUM -> exit 0."""
        bad = tmp_path / "bad.py"
        bad.write_text('X = "lin_api_FAKE_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n', encoding="utf-8")
        monkeypatch.setattr(cnlk, "BACKEND_DIR", tmp_path)
        rc = cnlk.main(["--root", str(tmp_path), "--severity", "critical"])
        # lin_api e HIGH, abaixo de critical, entao gate OK.
        assert rc == 0


# ============================================================================
# Pattern count — garantia de cobertura.
# ============================================================================
def test_pattern_catalog_has_15_plus_patterns() -> None:
    """Wave 48 G8.14.T3 — minimo 15 patterns (10 baseline + 5+ novos)."""
    assert len(cnlk.PATTERNS) >= 15, (
        f"Esperado >=15 patterns, achou {len(cnlk.PATTERNS)}: {[p.name for p in cnlk.PATTERNS]}"
    )
