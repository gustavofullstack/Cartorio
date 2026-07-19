"""G8.04.T2 — Empacotamento/export do system prompt do LobeChat (CartórioBot).

Carrega o prompt de sistema a partir de fontes conhecidas (com fallbacks) e
escreve um pacote offline sem segredos:

  out_dir/
    prompt.md        — texto do system prompt
    metadata.json    — version, sha256, source, exporter (sem tokens/API keys)

Fontes (prioridade):
  1. path explícito (preferred_source)
  2. infra/openclaw-agent/workspace/SOUL.md
  3. infra/lobechat/agent_cartorio_import.json → agents[].systemRole
  4. docs/lobechat/system_prompt.md | docs/system_prompt.md | docs/**/system_prompt.md
  5. .agents/system_prompt.md | .agents/**/system_prompt.md | .agents/**/persona*.md
  6. CARTORIO_DEFAULT_SYSTEM_PROMPT (embedded, HITL/LGPD-safe)

Modified by Gustavo Almeida — G8.04.T2.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.0"
EXPORTER_VERSION = "cartorio-lobechat-prompt-export-1.0"
PROMPT_FILENAME = "prompt.md"
METADATA_FILENAME = "metadata.json"

# Prompt curto, HITL + LGPD safe — sem PII, sem secrets, sem endpoints com tokens.
CARTORIO_DEFAULT_SYSTEM_PROMPT = """\
Você é o **CartórioBot**, assistente virtual do **2º Ofício de Notas de Uberlândia / MG**.

## Regras obrigatórias (HITL + LGPD)
1. **HITL**: você NÃO emite certidão, escritura, reconhecimento de firma nem valida isenção/urgência sozinho. Protocolos nascem como rascunho; escrevente humano valida atos jurídicos.
2. **LGPD**: nunca peça, repita ou envie CPF/RG/endereço completo a modelos externos. Se o usuário enviar PII, oriente handoff humano e não propague o dado.
3. **Tom**: PT-BR, cordial, direto, 1–3 frases. Sem floreios, sem conselho jurídico conclusivo.
4. **Escopo**: horário, endereço, orientação genérica de documentos, encaminhamento para agendamento e atendimento humano.
5. **Handoff**: dúvida jurídica complexa, reclamação, valor alto ou pedido de humano → transferir para escrevente (Chatwoot/HITL).

## Identidade
- Cartório: 2º Ofício de Notas de Uberlândia
- Horário: seg–sex 09h–17h
- Você informa e pré-qualifica; não substitui o tabelião.
"""

# Caminhos relativos à raiz do monorepo (ordem de prioridade).
DEFAULT_SOURCE_CANDIDATES: tuple[str, ...] = (
    "infra/openclaw-agent/workspace/SOUL.md",
    "infra/lobechat/agent_cartorio_import.json",
    "docs/lobechat/system_prompt.md",
    "docs/system_prompt.md",
    ".agents/system_prompt.md",
    ".agents/persona/system_prompt.md",
    ".agents/persona.md",
)

# Padrões para varredura em docs/ e .agents/ se candidatos fixos falharem.
_GLOB_FALLBACKS: tuple[str, ...] = (
    "docs/**/system_prompt.md",
    "docs/**/*persona*.md",
    ".agents/**/system_prompt.md",
    ".agents/**/*persona*.md",
)

# Redação defensiva — nunca exportar tokens/API keys literais no pacote.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret|bearer)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)ghp_[A-Za-z0-9]{20,}"),
)


@dataclass(frozen=True, slots=True)
class PromptLoadResult:
    """Resultado do carregamento do system prompt."""

    text: str
    source: str  # caminho relativo ou "embedded:CARTORIO_DEFAULT_SYSTEM_PROMPT"
    source_kind: str  # file | json_systemRole | embedded
    sha256: str
    char_count: int
    line_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def find_repo_root(start: Path | None = None) -> Path:
    """Sobe diretórios até achar marcadores do monorepo Cartorio."""
    cur = (start or Path(__file__).resolve()).resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if (candidate / "backend" / "app").is_dir() and (
            (candidate / "infra").is_dir() or (candidate / "SUPER_PLANO_G8_100_TASKS.md").is_file()
        ):
            return candidate
        if (candidate / "infra" / "lobechat").is_dir() and (candidate / "backend").is_dir():
            return candidate
    # Fallback: backend/app/services → parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def sha256_text(text: str) -> str:
    """SHA-256 hex do texto UTF-8 (sem BOM)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    """Remove padrões óbvios de segredo do texto exportado."""
    out = text
    for pat in _SECRET_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(0).split('=')[0].split(':')[0]}=***REDACTED***", out)
    return out


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_from_lobechat_json(path: Path) -> str | None:
    """Extrai systemRole do agent_cartorio_import.json (schemaVersion 1)."""
    try:
        data = json.loads(_read_text(path))
    except (json.JSONDecodeError, OSError):
        return None
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, list):
        return None
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        role = agent.get("systemRole") or agent.get("system_prompt") or agent.get("systemPrompt")
        if isinstance(role, str) and role.strip():
            return role.strip() + "\n"
    return None


def _try_load_path(path: Path, repo_root: Path) -> PromptLoadResult | None:
    if not path.is_file():
        return None
    try:
        rel = str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel = str(path)

    if path.suffix.lower() == ".json":
        text = _extract_from_lobechat_json(path)
        if not text:
            return None
        kind = "json_systemRole"
    else:
        text = _read_text(path)
        if not text.strip():
            return None
        kind = "file"

    cleaned = redact_secrets(text)
    return PromptLoadResult(
        text=cleaned if cleaned.endswith("\n") else cleaned + "\n",
        source=rel,
        source_kind=kind,
        sha256=sha256_text(cleaned if cleaned.endswith("\n") else cleaned + "\n"),
        char_count=len(cleaned),
        line_count=cleaned.count("\n") + (0 if cleaned.endswith("\n") else 1),
    )


def list_candidate_sources(repo_root: Path | None = None) -> list[Path]:
    """Lista caminhos candidatos que existem no disco (ordem de prioridade)."""
    root = repo_root or find_repo_root()
    seen: set[Path] = set()
    ordered: list[Path] = []

    def _add(p: Path) -> None:
        rp = p.resolve()
        if rp in seen:
            return
        seen.add(rp)
        if p.is_file():
            ordered.append(p)

    for rel in DEFAULT_SOURCE_CANDIDATES:
        _add(root / rel)

    for pattern in _GLOB_FALLBACKS:
        for match in sorted(root.glob(pattern)):
            _add(match)

    return ordered


def load_system_prompt(
    *,
    repo_root: Path | None = None,
    preferred_source: Path | str | None = None,
    allow_embedded: bool = True,
) -> PromptLoadResult:
    """Carrega system prompt com fallbacks.

    Raises:
        FileNotFoundError: se nenhuma fonte existir e allow_embedded=False.
    """
    root = repo_root or find_repo_root()

    if preferred_source is not None:
        pref = Path(preferred_source)
        if not pref.is_absolute():
            pref = root / pref
        result = _try_load_path(pref, root)
        if result is not None:
            return result
        raise FileNotFoundError(f"preferred_source não legível: {pref}")

    for path in list_candidate_sources(root):
        result = _try_load_path(path, root)
        if result is not None:
            return result

    if not allow_embedded:
        raise FileNotFoundError(
            "Nenhuma fonte de system prompt encontrada "
            f"(repo_root={root}; candidatos={list(DEFAULT_SOURCE_CANDIDATES)})"
        )

    text = CARTORIO_DEFAULT_SYSTEM_PROMPT
    if not text.endswith("\n"):
        text = text + "\n"
    return PromptLoadResult(
        text=text,
        source="embedded:CARTORIO_DEFAULT_SYSTEM_PROMPT",
        source_kind="embedded",
        sha256=sha256_text(text),
        char_count=len(text),
        line_count=text.count("\n"),
    )


def build_metadata(
    load: PromptLoadResult,
    *,
    out_dir: Path | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta metadata.json — sem secrets, sem PII."""
    meta: dict[str, Any] = {
        "package_version": PACKAGE_VERSION,
        "exporter_version": EXPORTER_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prompt_file": PROMPT_FILENAME,
        "prompt_sha256": load.sha256,
        "prompt_char_count": load.char_count,
        "prompt_line_count": load.line_count,
        "source": load.source,
        "source_kind": load.source_kind,
        "hitl_required": True,
        "lgpd_safe_export": True,
        "contains_secrets": False,
        "purpose": "LobeChat CartórioBot system prompt package (import/sync)",
        "notes": [
            "Pacote offline — sem API keys, tokens ou passwords.",
            "Revalidar HITL/LGPD após import no LobeChat UI.",
            "Fonte canônica OpenClaw: infra/openclaw-agent/workspace/SOUL.md",
        ],
    }
    if out_dir is not None:
        meta["out_dir"] = str(out_dir)
    if extra:
        # Nunca mergear chaves sensíveis
        banned = {"api_key", "apikey", "token", "password", "secret", "authorization"}
        for k, v in extra.items():
            if k.lower() in banned or any(b in k.lower() for b in banned):
                continue
            meta[k] = v
    return meta


def export_package(
    out_dir: Path | str,
    *,
    repo_root: Path | None = None,
    preferred_source: Path | str | None = None,
    allow_embedded: bool = True,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exporta prompt.md + metadata.json em out_dir.

    Returns:
        dict com paths escritos + metadata (inclui prompt_sha256).
    """
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    load = load_system_prompt(
        repo_root=repo_root,
        preferred_source=preferred_source,
        allow_embedded=allow_embedded,
    )
    prompt_path = target / PROMPT_FILENAME
    meta_path = target / METADATA_FILENAME

    prompt_path.write_text(load.text, encoding="utf-8")
    metadata = build_metadata(load, out_dir=target, extra=extra_metadata)
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Re-hash do arquivo escrito (confirma I/O)
    written = prompt_path.read_text(encoding="utf-8")
    written_hash = sha256_text(written)
    if written_hash != load.sha256:
        # Normalização de newline — atualiza metadata
        metadata["prompt_sha256"] = written_hash
        metadata["prompt_char_count"] = len(written)
        metadata["prompt_line_count"] = written.count("\n") + (0 if written.endswith("\n") else 1)
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "ok": True,
        "out_dir": str(target.resolve()),
        "prompt_path": str(prompt_path.resolve()),
        "metadata_path": str(meta_path.resolve()),
        "prompt_sha256": metadata["prompt_sha256"],
        "source": load.source,
        "source_kind": load.source_kind,
        "package_version": PACKAGE_VERSION,
        "metadata": metadata,
    }


__all__ = [
    "CARTORIO_DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_SOURCE_CANDIDATES",
    "EXPORTER_VERSION",
    "METADATA_FILENAME",
    "PACKAGE_VERSION",
    "PROMPT_FILENAME",
    "PromptLoadResult",
    "build_metadata",
    "export_package",
    "find_repo_root",
    "list_candidate_sources",
    "load_system_prompt",
    "redact_secrets",
    "sha256_text",
]
