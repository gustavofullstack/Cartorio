from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
EXPECTED_JOBS = {"lint", "test", "docs-build", "all-green"}
CACHED_ARTIFACTS = {
    "backend/.pytest_cache",
    "backend/.mypy_cache",
    "backend/.ruff_cache",
    "backend/htmlcov/",
}


def _load_ci() -> dict[str, Any]:
    parsed = yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def _steps(ci_config: dict[str, Any], job_name: str) -> list[dict[str, Any]]:
    steps = ci_config["jobs"][job_name]["steps"]
    assert isinstance(steps, list)
    return steps


def test_ci_yaml_valid() -> None:
    ci_config = _load_ci()

    assert ci_config["name"] == "CI"
    assert EXPECTED_JOBS <= set(ci_config["jobs"])
    assert all(_steps(ci_config, job_name) for job_name in EXPECTED_JOBS)


def test_cache_step_present() -> None:
    ci_config = _load_ci()
    cached_paths: set[str] = set()

    for job_name in ("lint", "test"):
        steps = _steps(ci_config, job_name)
        setup_python = next(step for step in steps if step.get("uses") == "actions/setup-python@v5")
        setup_uv = next(step for step in steps if step.get("uses") == "astral-sh/setup-uv@v4")
        assert setup_python["with"]["cache"] == "pip"
        assert setup_uv["with"]["enable-cache"] is True

        for step in steps:
            if step.get("uses") == "actions/cache@v4":
                cached_paths.update(step["with"]["path"].splitlines())

    assert CACHED_ARTIFACTS <= cached_paths


def test_uv_lock_in_dependency_path() -> None:
    ci_config = _load_ci()

    for job_name in ("lint", "test"):
        steps = _steps(ci_config, job_name)
        setup_python = next(step for step in steps if step.get("uses") == "actions/setup-python@v5")
        setup_uv = next(step for step in steps if step.get("uses") == "astral-sh/setup-uv@v4")
        assert setup_python["with"]["cache-dependency-path"] == "backend/uv.lock"
        assert setup_uv["with"]["cache-dependency-glob"] == "backend/uv.lock"
