"""Cobertura mínima de registro de rotas críticas em app.main."""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app


def _route_paths() -> set[str]:
    paths: set[str] = set()
    for route in app.router.routes:
        if isinstance(route, APIRoute):
            paths.add(route.path)
            continue

        effective_candidates = getattr(route, "_effective_candidates", ())
        for effective_route in effective_candidates:
            candidate_path = getattr(effective_route, "path", None)
            if candidate_path:
                paths.add(candidate_path)
    return paths


def test_main_router_registers_lark_webhook_and_whatsapp_routes() -> None:
    paths = _route_paths()
    assert "/api/v1/lark/webhook/lark" in paths
    assert "/api/v1/whatsapp/webhook" in paths
