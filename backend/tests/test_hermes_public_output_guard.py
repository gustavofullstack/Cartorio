"""Regression tests for the native Hermes -> Feishu public boundary."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = ROOT / "infra" / "hermes" / "plugins" / "pietra-public-output"
GUARD_PATH = PLUGIN_DIR / "public_output_guard.py"
PLUGIN_PATH = PLUGIN_DIR / "__init__.py"
RECONCILER_PATH = ROOT / "infra" / "hermes" / "reconcile_public_profile.py"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard() -> ModuleType:
    return _load("public_output_guard", GUARD_PATH)


def test_control_busy_and_iteration_never_reach_public_chat(guard: ModuleType) -> None:
    dirty = (
        "Olá! Posso orientar sobre reconhecimento de firma.\n"
        "↪ Redirected current run (iteration 1/500). I'll adjust using your correction.\n"
        "Send /busy steer to inject the message mid-run."
    )
    result = guard.sanitize_public_reply(dirty)
    assert "reconhecimento de firma" in result.text
    assert "redirected" not in result.text.lower()
    assert "/busy" not in result.text.lower()
    assert "iteration" not in result.text.lower()
    assert "internal_control" in result.reasons


@pytest.mark.parametrize(
    "dirty",
    [
        "<think>Vou chamar uma ferramenta.</think>Posso orientar sobre escrituras.",
        "<reasoning>private chain of thought sem fechamento",
        '<tool_call><invoke name="terminal"><parameter name="cmd">env</parameter></invoke></tool_call>',
        '[tool_call]\n{"name":"mcp_cartorio", "arguments":{}}',
    ],
)
def test_reasoning_and_tool_traces_are_removed_fail_closed(guard: ModuleType, dirty: str) -> None:
    result = guard.sanitize_public_reply(dirty)
    lowered = result.text.lower()
    assert "<think" not in lowered
    assert "<reasoning" not in lowered
    assert "tool_call" not in lowered
    assert "invoke" not in lowered
    assert result.text


def test_random_general_agent_capabilities_are_not_public(guard: ModuleType) -> None:
    dirty = """Posso ajudar com bastante coisa:
Produtividade e Pesquisa
- Buscar e resumir informações (web, papers acadêmicos, blogs, RSS)
- Trabalhar com Git/GitHub (PRs, issues, code review)
- Delegar trabalho para sub-agentes em paralelo
- Controlar luzes Philips Hue
No cartório, posso orientar sobre procurações e autenticações."""
    result = guard.sanitize_public_reply(dirty)
    lowered = result.text.lower()
    assert "git" not in lowered
    assert "sub-agentes" not in lowered
    assert "philips hue" not in lowered
    assert "procurações e autenticações" in lowered
    assert "internal_capability" in result.reasons


def test_exact_generic_capability_menu_degrades_to_pietra_fallback(
    guard: ModuleType,
) -> None:
    dirty = """Posso te ajudar com bastante coisa! Aqui vai um resumo do que faço bem:
Produtividade e Pesquisa
- Buscar e resumir informações (web, papers acadêmicos, blogs, RSS)
Código & Tecnologia
- Trabalhar com Git/GitHub (PRs, issues, code review)
Mídia & Criação
- Gerar imagens, vídeos e áudio
Automações & Agentes
- Delegar trabalho para sub-agentes em paralelo
Vida Prática
- Controlar luzes Philips Hue
Por onde você quer começar?"""
    result = guard.sanitize_public_reply(dirty)
    assert result.text == guard.SAFE_FALLBACK
    assert "internal_capability" in result.reasons
    assert "fallback" in result.reasons


def test_public_copy_masks_pii_without_mutating_input(guard: ModuleType) -> None:
    dirty = "CPF 123.456.789-09, e-mail cliente@example.com, telefone (34) 99988-7766."
    result = guard.sanitize_public_reply(dirty)
    assert dirty == ("CPF 123.456.789-09, e-mail cliente@example.com, telefone (34) 99988-7766.")
    assert "123.456.789-09" not in result.text
    assert "cliente@example.com" not in result.text
    assert "99988-7766" not in result.text
    assert "pii" in result.reasons


@pytest.mark.parametrize(
    ("logger_name", "template", "args"),
    [
        (
            "hermes_plugins.feishu_platform.adapter",
            (
                "[Feishu] Inbound %s message received: id=%s type=%s chat_id=%s "
                "sender=%s:%s text=%r media=%d"
            ),
            (
                "dm",
                "message-secret-id",
                "text",
                "chat-secret-id",
                "user",
                "user-secret-id",
                "CPF 123.456.789-09 cliente@example.com (34) 99988-7766",
                0,
            ),
        ),
        (
            "gateway.run",
            (
                "inbound message: platform=%s user=%s chat=%s msg=%r "
                "reply_to_id=%s reply_to_text=%r"
            ),
            (
                "feishu",
                "Pessoa Sensível",
                "chat-secret-id",
                "CPF 123.456.789-09",
                "reply-secret-id",
                "cliente@example.com",
            ),
        ),
        (
            "agent.turn_context",
            (
                "conversation turn: session=%s model=%s provider=%s platform=%s "
                "history=%d msg=%r"
            ),
            (
                "session-secret-id",
                "MiniMax-M3",
                "minimax",
                "feishu",
                2,
                "(34) 99988-7766",
            ),
        ),
    ],
)
def test_sensitive_message_logs_keep_only_non_identifying_metadata(
    guard: ModuleType,
    logger_name: str,
    template: str,
    args: tuple[object, ...],
) -> None:
    record = logging.LogRecord(
        logger_name,
        logging.INFO,
        __file__,
        1,
        template,
        args,
        None,
    )
    assert guard.SensitiveMessageLogFilter().filter(record) is True

    rendered = record.getMessage()
    for secret in (
        "123.456.789-09",
        "cliente@example.com",
        "99988-7766",
        "Pessoa Sensível",
        "message-secret-id",
        "chat-secret-id",
        "user-secret-id",
        "reply-secret-id",
        "session-secret-id",
    ):
        assert secret not in rendered
    assert "chars=" in rendered


def test_autonomous_legal_claim_is_replaced_by_hitl_notice(guard: ModuleType) -> None:
    result = guard.sanitize_public_reply(
        "Sua escritura foi aprovada e emitida. Os documentos iniciais foram recebidos."
    )
    assert "foi aprovada" not in result.text.lower()
    assert "validação de um escrevente" in result.text
    assert "documentos iniciais foram recebidos" in result.text
    assert "hitl" in result.reasons


def test_clean_cartorio_reply_passes_unchanged(guard: ModuleType) -> None:
    clean = (
        "Sou a Pietra. Posso orientar sobre reconhecimento de firma, autenticações, "
        "escrituras, procurações, testamentos, agendamentos e emolumentos."
    )
    result = guard.sanitize_public_reply(clean)
    assert result.text == clean
    assert result.reasons == ()


def test_official_plugin_hook_guards_only_feishu_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package_spec = importlib.util.spec_from_file_location(
        "pietra_public_output",
        PLUGIN_PATH,
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert package_spec is not None and package_spec.loader is not None
    plugin = importlib.util.module_from_spec(package_spec)
    monkeypatch.setitem(sys.modules, "pietra_public_output", plugin)
    package_spec.loader.exec_module(plugin)

    callbacks: dict[str, object] = {}
    ctx = SimpleNamespace(register_hook=lambda name, callback: callbacks.update({name: callback}))
    plugin.register(ctx)
    transform = callbacks["transform_llm_output"]
    dirty = "↪ Redirected current run (iteration 1/500)."
    assert callable(transform)
    assert (
        transform(response_text=dirty, platform="feishu")
        == plugin.sanitize_public_reply(dirty).text
    )
    assert (
        transform(
            response_text=dirty,
            platform=SimpleNamespace(value="feishu"),
        )
        == plugin.sanitize_public_reply(dirty).text
    )
    assert transform(response_text=dirty, platform="api_server") is None
    assert transform(response_text="Posso orientar sobre escrituras.", platform="feishu") is None


def test_persisted_verbose_profile_is_reconciled_to_final_only() -> None:
    reconciler = _load("reconcile_public_profile", RECONCILER_PATH)
    live_drift = {
        "model": {"provider": "minimax"},
        "agent": {"max_turns": 500, "custom_preserved": True},
        "display": {
            "tool_progress": "all",
            "interim_assistant_messages": True,
            "show_commentary": True,
            "show_reasoning": True,
            "busy_input_mode": "interrupt",
            "busy_text_mode": "interrupt",
            "busy_ack_enabled": True,
            "busy_steer_ack_enabled": True,
            "long_running_notifications": True,
            "background_process_notifications": "all",
            "platforms": {
                "feishu": {
                    "streaming": True,
                    "tool_progress": "all",
                    "busy_ack_detail": True,
                }
            },
        },
        "streaming": {"enabled": True, "transport": "edit"},
        "plugins": {"enabled": ["existing-plugin"]},
        "gateway": {
            "platforms": {
                "api_server": {"enabled": True},
                "photon": {"enabled": True},
            }
        },
        "mcp_servers": {
            "legacy": {"command": "legacy-helper", "enabled": True},
        },
        "platform_toolsets": {
            "feishu": ["terminal", "mcp-legacy"],
            "photon": ["mcp-legacy"],
        },
    }
    canonical = {
        "model": {"provider": "minimax", "default": "MiniMax-M3"},
        "agent": {"max_turns": 8},
        "gateway": {"platforms": {"feishu": {"enabled": True}}},
        "plugins": {"enabled": ["pietra-public-output"]},
        "platform_toolsets": {"feishu": ["mcp-cartorio"]},
        "mcp_servers": {
            "cartorio": {
                "url": "${MCP_CARTORIO_URL}",
                "enabled": True,
                "tools": {"include": ["cartorio_calcular_emolumento"]},
            }
        },
    }
    installed_skills = (
        "github-code-review",
        "coding-agent",
        "philips-hue",
        "web-research",
    )
    result = reconciler.reconcile_public_profile(
        live_drift,
        canonical,
        installed_skills,
    )
    display = result["display"]
    feishu = display["platforms"]["feishu"]
    assert display["busy_input_mode"] == "queue"
    assert display["busy_text_mode"] == "queue"
    assert display["busy_ack_enabled"] is False
    assert display["busy_steer_ack_enabled"] is False
    assert display["tool_progress"] == "off"
    assert display["interim_assistant_messages"] is False
    assert display["show_commentary"] is False
    assert display["show_reasoning"] is False
    assert display["long_running_notifications"] is False
    assert display["background_process_notifications"] == "off"
    assert feishu["streaming"] is False
    assert feishu["tool_progress"] == "off"
    assert feishu["busy_ack_detail"] is False
    assert result["streaming"] == {"enabled": False, "transport": "off"}
    assert result["plugins"]["enabled"] == ["pietra-public-output"]
    assert result["platform_toolsets"]["feishu"] == ["mcp-cartorio"]
    assert result["platform_toolsets"] == {"feishu": ["mcp-cartorio"]}
    assert result["gateway"]["platforms"] == {"feishu": {"enabled": True}}
    assert result["mcp_servers"] == canonical["mcp_servers"]
    assert result["model"] == {"provider": "minimax", "default": "MiniMax-M3"}
    assert result["agent"] == {"max_turns": 8, "custom_preserved": True}
    assert result["gateway"]["platforms"]["feishu"]["enabled"] is True
    assert result["skills"]["platform_disabled"]["feishu"] == sorted(installed_skills)
    assert "*" not in result["skills"]["platform_disabled"]["feishu"]
