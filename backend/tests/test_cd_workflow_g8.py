"""G8.14.T2 — Conditional deploys on absolute quality gates.

Validates the CI/CD workflow topology: every CI job must be green
before CD deploy can fire. Reads .github/workflows/{ci,cd}.yml
as YAML and asserts the topology matches the G8.14.T2 contract:
- ci.yml has a `secrets-scan` job (gitleaks + literal keys fallback).
- cd.yml has a `quality-gate` job dependent on CI success.
- cd.yml `deploy-render` job requires `quality-gate` to succeed.
- Every CI job has a `timeout-minutes` set (fail-safe if hang).
- ci.yml `all-green` aggregator requires all 4 jobs.

Modified by Gustavo Almeida — cartorio-sre / Wave 48.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
CD_PATH = ROOT / ".github" / "workflows" / "cd.yml"


@pytest.fixture(scope="module")
def ci_yaml() -> dict[str, object]:
    return yaml.safe_load(CI_PATH.read_text())


@pytest.fixture(scope="module")
def cd_yaml() -> dict[str, object]:
    return yaml.safe_load(CD_PATH.read_text())


def test_cd_yaml_is_valid_yaml_with_required_jobs(cd_yaml: dict[str, object]) -> None:
    """cd.yml parses and has the two top-level jobs."""
    assert "jobs" in cd_yaml
    jobs = cd_yaml["jobs"]
    assert isinstance(jobs, dict)
    assert "quality-gate" in jobs
    assert "deploy-render" in jobs


def test_quality_gate_is_driven_by_successful_ci_workflow(cd_yaml: dict[str, object]) -> None:
    """quality-gate follows the canonical CI workflow and cannot self-trigger."""
    qg = cd_yaml["jobs"]["quality-gate"]
    assert isinstance(qg, dict)
    assert "needs" not in qg, "needs cannot reference a job in another workflow"
    assert "if" in qg, "quality-gate must have an `if:` guard"
    if_str = str(qg["if"])
    for required in (
        "workflow_run",
        "workflow_run.name == 'CI'",
        "workflow_run.event == 'push'",
        "workflow_run.head_branch == 'master'",
        "workflow_run.conclusion == 'success'",
    ):
        assert required in if_str, f"quality gate guard missing {required!r}: {if_str!r}"
    assert "\n  push:" not in CD_PATH.read_text(), (
        "CD must not self-trigger on push independently of CI"
    )
    steps = qg["steps"]
    assert isinstance(steps, list)
    step_names = [s.get("name", "") for s in steps]
    assert any("Ruff" in n for n in step_names), "lint gate missing"
    assert any("Mypy" in n for n in step_names), "mypy gate missing"
    assert any("Pytest" in n for n in step_names), "pytest gate missing"
    assert any("Secrets" in n for n in step_names), "secrets gate missing"
    assert any("PII" in n for n in step_names), "LGPD PII gate missing"


def test_quality_gate_has_valid_synthetic_runtime_environment(cd_yaml: dict[str, object]) -> None:
    """CD's isolated pytest gate must satisfy the Settings contract."""
    qg = cd_yaml["jobs"]["quality-gate"]
    assert isinstance(qg, dict)
    assert qg["timeout-minutes"] >= 20
    services = qg.get("services")
    assert isinstance(services, dict)
    assert "postgres" in services and "redis" in services
    pytest_step = next(step for step in qg["steps"] if "Pytest" in step.get("name", ""))
    env = pytest_step["env"]
    assert env["APP_ENV"] == "test"
    assert len(env["AUDIT_HMAC_KEY"]) >= 32
    assert re.fullmatch(r"[a-f0-9]{64}", env["CARTORIO_API_KEY"])
    assert "--dist loadfile" in pytest_step["run"]


def test_checkout_pins_validated_ci_sha(cd_yaml: dict[str, object]) -> None:
    qg = cd_yaml["jobs"]["quality-gate"]
    checkout = next(step for step in qg["steps"] if step.get("uses") == "actions/checkout@v4")
    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"


def test_deploy_render_needs_quality_gate(cd_yaml: dict[str, object]) -> None:
    """deploy-render only runs when quality-gate is success (fail-safe)."""
    deploy = cd_yaml["jobs"]["deploy-render"]
    assert isinstance(deploy, dict)
    needs = deploy.get("needs")
    assert needs is not None, (
        "deploy-render must declare `needs:` (no implicit run is the default — "
        "it would always trigger on push to master)"
    )
    if isinstance(needs, str):
        assert needs == "quality-gate", f"needs must be 'quality-gate', got {needs!r}"
    elif isinstance(needs, list):
        assert "quality-gate" in needs, (
            f"deploy-render needs list must contain 'quality-gate', got {needs!r}"
        )
    guard = str(deploy.get("if", ""))
    assert "quality-gate.result" in guard
    assert "vars.RENDER_DEPLOY_ENABLED == 'true'" in guard
    assert "vars.SUI_CHECKLIST_APPROVED == 'true'" in guard
    assert "workflow_dispatch" not in guard, "manual dispatch must not bypass SUI/CI gates"


def test_ci_yaml_has_secrets_scan_job(ci_yaml: dict[str, object]) -> None:
    """ci.yml must have a secrets-scan job (gitleaks or equivalent)."""
    jobs = ci_yaml["jobs"]
    assert isinstance(jobs, dict)
    assert "secrets-scan" in jobs, f"secrets-scan job required, got jobs: {sorted(jobs.keys())}"
    scan = jobs["secrets-scan"]
    assert isinstance(scan, dict)
    steps = scan["steps"]
    step_uses = [s.get("uses", "") for s in steps if isinstance(s, dict)]
    gitleaks = any("gitleaks" in u for u in step_uses)
    fallback = any(
        "check_no_literal_keys" in s.get("run", "") for s in steps if isinstance(s, dict)
    )
    assert gitleaks or fallback, (
        f"secrets-scan must use gitleaks action OR run check_no_literal_keys.py, "
        f"got uses={[u for u in step_uses if u]}"
    )


def test_ci_literal_key_scan_is_a_hard_gate(ci_yaml: dict[str, object]) -> None:
    """Critical literal-key findings cannot be converted into a successful CI job."""
    jobs = ci_yaml["jobs"]
    assert isinstance(jobs, dict)
    scan = jobs["secrets-scan"]
    assert isinstance(scan, dict)
    steps = scan["steps"]
    assert isinstance(steps, list)
    literal_steps = [
        step
        for step in steps
        if isinstance(step, dict) and "check_no_literal_keys.py" in str(step.get("run", ""))
    ]
    assert len(literal_steps) == 1, "secrets-scan must contain exactly one literal-key gate"
    literal_step = literal_steps[0]
    assert literal_step.get("continue-on-error") is not True
    command = str(literal_step["run"])
    assert "--report-only" not in command
    assert "|| true" not in command


def test_ci_all_jobs_have_timeout_minutes(ci_yaml: dict[str, object]) -> None:
    """Each CI job must declare timeout-minutes (no hung runs)."""
    jobs = ci_yaml["jobs"]
    assert isinstance(jobs, dict)
    for name, body in jobs.items():
        assert isinstance(body, dict), f"job {name} not a dict"
        assert "timeout-minutes" in body, f"job {name} missing timeout-minutes (hung-run fail-safe)"
        tmo = body["timeout-minutes"]
        assert isinstance(tmo, int) and 0 < tmo <= 60, (
            f"job {name} timeout-minutes must be int in (0, 60], got {tmo!r}"
        )


def test_ci_all_green_aggregates_all_four_jobs(ci_yaml: dict[str, object]) -> None:
    """all-green job needs secrets-scan + lint + test + docs-build."""
    ag = ci_yaml["jobs"]["all-green"]
    assert isinstance(ag, dict)
    needs = ag["needs"]
    assert isinstance(needs, list)
    for required in ("secrets-scan", "lint", "test", "docs-build"):
        assert required in needs, f"all-green needs list must include {required!r}, got {needs!r}"
