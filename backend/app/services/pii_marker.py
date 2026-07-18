"""Pydantic Field helpers + PII markers (G8.17.T2).

LGPD Art. 46: campos que carregam dados pessoais devem ser explicitamente
marcados para que ferramentas automatizadas (linters, audit scanners, OpenAPI
generators) possam sinalizar/filtrar/redatar sem dependencia de introspeccao
manual.

Uso canonico:

    from app.services.pii_marker import PIIField, PII, masked

    class TelegramMessage(BaseModel):
        text: Annotated[str | None, PIIField(description="Texto da mensagem")]
        from_user: Annotated[TelegramUser | None, PIIField(description="Remetente")]

A constante PII e apenas um marker semantico (string constante) usado em
`Field(..., description=f"{PII} ...")` ou em `Annotated[str, PII]`.

Backward compat: este modulo nao depende de pydantic alem de Field/Annotated
- funciona com Pydantic v1.10+ e v2+. Marcador puramente documentacional
para tools externas (OpenAPI extension `x-pii-fields`, scanners LGPD).
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

PII: str = "**LGPD PII**"


def PIIField(  # noqa: N802 - nome canonico segue convencao Pydantic Field
    *,
    description: str,
    examples: list[Any] | None = None,
    default: Any = ...,
    **kwargs: Any,
) -> Any:
    """Pydantic Field com prefixo `**LGPD PII**` automatico na description.

    Garante que todo campo com PII tem seu marker visivel no OpenAPI gerado.
    Caller passa description livre - prefixo eh injetado aqui.

    Args:
        description: descricao humanamente util (sem o prefixo LGPD PII).
        examples: lista de exemplos (opcional).
        default: valor default (use ... para required).
        **kwargs: forwarded a pydantic.Field (max_length, ge, etc).

    Returns:
        Pydantic FieldInfo com description prefixada e json_schema_extra
        anotando o campo como PII para tools externas (OpenAPI x-pii).
    """
    if not description.startswith(PII):
        description = f"{PII} {description}"
    js_extra = kwargs.pop("json_schema_extra", None) or {}
    js_extra = {**js_extra, "x-pii": True}
    return Field(
        default=default,
        description=description,
        examples=examples,
        json_schema_extra=js_extra,
        **kwargs,
    )


PIIAnnotation = Annotated[Any, PII]


def is_pii_field(description: str | None) -> bool:
    """Retorna True se a description comeca com o marker `**LGPD PII**`."""
    return description is not None and description.startswith(PII)


def collect_pii_paths(model: type[Any]) -> list[str]:
    """Coleta paths (JSON pointer-like) dos campos PII de um Pydantic model.

    Ex: `collect_pii_paths(TelegramUpdate)` -> `['message.from.id', 'chat.id']`.

    Usado para popular a OpenAPI extension `x-pii-fields` em endpoints que
    recebem esse schema.
    """
    paths: list[str] = []
    try:
        schema = model.model_json_schema()
    except Exception:
        return paths
    _walk_schema(schema, prefix="", out=paths)
    return paths


def _walk_schema(schema: dict[str, Any], prefix: str, out: list[str]) -> None:
    """Walk recursivo do JSON schema, coletando paths com `x-pii: True`."""
    props = schema.get("properties", {})
    for name, prop in props.items():
        cur = f"{prefix}.{name}" if prefix else name
        if prop.get("x-pii") is True:
            out.append(cur)
        if prop.get("type") == "object":
            _walk_schema(prop, cur, out)


__all__ = [
    "PII",
    "PIIField",
    "PIIAnnotation",
    "is_pii_field",
    "collect_pii_paths",
]
