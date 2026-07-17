"""G8.04.T4 — Traefik LobeChat → multi OpenClaw routing (YAML + validator).

Cobre:
- parse_yaml_or_dict (path, str YAML, dict)
- validate_routing no template versionado (ok)
- routers/services obrigatórios
- weighted openclaw-a/openclaw-b
- failover mode aceito
- rejeição de secrets
- load_default_template + find_repo_root

Modified by Gustavo Almeida — G8.04.T4 Wave 32.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.services.traefik_lobechat_routing import (
    DEFAULT_TEMPLATE_REL,
    REQUIRED_ROUTERS,
    REQUIRED_SERVICES,
    RoutingValidationResult,
    find_repo_root,
    load_default_template,
    parse_yaml_or_dict,
    validate_routing,
)

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
TEMPLATE = REPO / DEFAULT_TEMPLATE_REL


def _minimal_weighted_config() -> dict[str, Any]:
    return {
        'http': {
            'routers': {
                'lobechat': {
                    'rule': 'Host(`lobe.example.test`)',
                    'service': 'lobechat',
                },
                'openclaw-pool': {
                    'rule': 'Host(`agent.example.test`)',
                    'service': 'openclaw-pool',
                },
            },
            'services': {
                'lobechat': {
                    'loadBalancer': {
                        'servers': [{'url': 'http://cartorio_lobechat:3210'}],
                    },
                },
                'openclaw-pool': {
                    'weighted': {
                        'services': [
                            {'name': 'openclaw-a', 'weight': 90},
                            {'name': 'openclaw-b', 'weight': 10},
                        ],
                    },
                },
                'openclaw-a': {
                    'loadBalancer': {
                        'servers': [{'url': 'http://cartorio_openclaw-gateway:18789'}],
                    },
                },
                'openclaw-b': {
                    'loadBalancer': {
                        'servers': [{'url': 'http://cartorio_openclaw-gateway-b:18789'}],
                    },
                },
            },
        },
    }


def _minimal_failover_config() -> dict[str, Any]:
    cfg = _minimal_weighted_config()
    cfg['http']['services']['openclaw-pool'] = {
        'failover': {
            'service': 'openclaw-a',
            'fallback': 'openclaw-b',
        },
    }
    return cfg


class TestFindRepoAndTemplate:
    def test_find_repo_root(self) -> None:
        root = find_repo_root(BACKEND)
        assert (root / 'backend').is_dir()
        assert (root / 'infra').is_dir()

    def test_default_template_exists(self) -> None:
        assert TEMPLATE.is_file(), f'missing template: {TEMPLATE}'

    def test_load_default_template(self) -> None:
        data = load_default_template(REPO)
        assert 'http' in data
        assert 'routers' in data['http']
        assert 'services' in data['http']


class TestParseYamlOrDict:
    def test_parse_dict_passthrough(self) -> None:
        src = {'http': {'routers': {}}}
        out = parse_yaml_or_dict(src)
        assert out == src
        assert out is not src  # shallow copy

    def test_parse_yaml_string(self) -> None:
        text = 'http:\n  routers:\n    lobechat:\n      rule: Host(`x`)\n'
        out = parse_yaml_or_dict(text)
        assert out['http']['routers']['lobechat']['rule'] == 'Host(`x`)'

    def test_parse_path(self) -> None:
        out = parse_yaml_or_dict(TEMPLATE)
        assert 'http' in out

    def test_parse_path_string(self) -> None:
        out = parse_yaml_or_dict(str(TEMPLATE))
        assert 'services' in out['http']

    def test_parse_empty_raises(self) -> None:
        with pytest.raises(ValueError, match='empty'):
            parse_yaml_or_dict('   \n')

    def test_parse_non_mapping_raises(self) -> None:
        with pytest.raises(ValueError, match='mapping'):
            parse_yaml_or_dict('- just\n- a\n- list\n')

    def test_parse_invalid_yaml_raises(self) -> None:
        with pytest.raises(ValueError, match='invalid YAML'):
            parse_yaml_or_dict('http: [\n  unclosed')

    def test_parse_unsupported_type(self) -> None:
        with pytest.raises(TypeError):
            parse_yaml_or_dict(12345)  # type: ignore[arg-type]


class TestValidateRoutingOk:
    def test_template_file_validates(self) -> None:
        result = validate_routing(TEMPLATE)
        assert isinstance(result, RoutingValidationResult)
        assert result.ok is True, result.errors
        assert result.openclaw_mode == 'weighted'
        assert set(REQUIRED_ROUTERS).issubset(set(result.routers))
        assert set(REQUIRED_SERVICES).issubset(set(result.services))
        d = result.to_dict()
        assert d['ok'] is True
        assert 'token' not in str(d).lower() or 'secret-like' not in str(d)

    def test_minimal_weighted_ok(self) -> None:
        result = validate_routing(_minimal_weighted_config())
        assert result.ok is True
        assert result.openclaw_mode == 'weighted'
        assert result.errors == ()

    def test_minimal_failover_ok(self) -> None:
        result = validate_routing(_minimal_failover_config())
        assert result.ok is True, result.errors
        assert result.openclaw_mode == 'failover'

    def test_template_yaml_roundtrip(self) -> None:
        raw = TEMPLATE.read_text(encoding='utf-8')
        data = yaml.safe_load(raw)
        result = validate_routing(data)
        assert result.ok is True
        # Artifact must document multi-node names.
        services = data['http']['services']
        assert 'openclaw-a' in services
        assert 'openclaw-b' in services
        weights = services['openclaw-pool']['weighted']['services']
        names = {w['name'] for w in weights}
        assert names == {'openclaw-a', 'openclaw-b'}


class TestValidateRoutingFailures:
    def test_missing_http(self) -> None:
        result = validate_routing({})
        assert result.ok is False
        assert any('http' in e for e in result.errors)

    def test_missing_required_routers(self) -> None:
        cfg = _minimal_weighted_config()
        del cfg['http']['routers']['lobechat']
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('lobechat' in e and 'router' in e for e in result.errors)

    def test_missing_openclaw_b_service(self) -> None:
        cfg = _minimal_weighted_config()
        del cfg['http']['services']['openclaw-b']
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('openclaw-b' in e for e in result.errors)

    def test_weighted_missing_node_ref(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['http']['services']['openclaw-pool']['weighted']['services'] = [
            {'name': 'openclaw-a', 'weight': 100},
        ]
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('openclaw-b' in e for e in result.errors)

    def test_pool_as_plain_loadbalancer_rejected(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['http']['services']['openclaw-pool'] = {
            'loadBalancer': {
                'servers': [{'url': 'http://cartorio_openclaw-gateway:18789'}],
            },
        }
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('weighted' in e or 'failover' in e for e in result.errors)

    def test_router_unknown_service(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['http']['routers']['lobechat']['service'] = 'does-not-exist'
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('unknown service' in e for e in result.errors)

    def test_node_missing_server_url(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['http']['services']['openclaw-a'] = {'loadBalancer': {'servers': []}}
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('openclaw-a' in e and 'url' in e for e in result.errors)

    def test_rejects_secret_like_api_key(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['http']['middlewares'] = {
            'auth': {'headers': {'customRequestHeaders': {'Authorization': 'Bearer abcdefghijklmnopqrstuvwxyz012345'}}},
        }
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('secret' in e.lower() for e in result.errors)
        # Não ecoar o bearer no reasons.
        joined = ' '.join(result.errors + result.warnings)
        assert 'abcdefghijklmnopqrstuvwxyz012345' not in joined

    def test_rejects_sk_token_in_string(self) -> None:
        cfg = _minimal_weighted_config()
        cfg['meta'] = 'provider key sk-abcdefghijklmnopqrstuvwxyz'
        result = validate_routing(cfg)
        assert result.ok is False
        assert any('secret' in e.lower() for e in result.errors)

    def test_parse_error_path(self) -> None:
        result = validate_routing('http: [\n  bad')
        assert result.ok is False
        assert any('parse error' in e for e in result.errors)

    def test_template_has_no_literal_secrets(self) -> None:
        text = TEMPLATE.read_text(encoding='utf-8').lower()
        for bad in ('sk-', 'api_key=', 'password=', 'bearer ey', '-----begin'):
            assert bad not in text


class TestConstants:
    def test_required_sets(self) -> None:
        assert 'lobechat' in REQUIRED_ROUTERS
        assert 'openclaw-pool' in REQUIRED_ROUTERS
        assert REQUIRED_SERVICES >= {'lobechat', 'openclaw-a', 'openclaw-b', 'openclaw-pool'}
