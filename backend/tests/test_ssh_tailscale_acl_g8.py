"""G8.09.T4 — SSH Tailscale ACL / authorized peers tests.

Modified by Gustavo Almeida — Wave 37 Squad 09.
"""

from __future__ import annotations

from app.services.ssh_tailscale_acl import (
    DEFAULT_PEERS,
    VPS_TAILSCALE_IP,
    AuthorizedPeer,
    inventory_report,
    is_ssh_source_allowed,
    list_authorized_ips,
    peer_by_ip,
    recommended_sshd_snippet,
    validate_sshd_match_block,
)


def test_default_peers_include_vps_admin() -> None:
    ips = {p.ip for p in DEFAULT_PEERS}
    assert VPS_TAILSCALE_IP in ips
    vps = peer_by_ip(VPS_TAILSCALE_IP)
    assert vps is not None
    assert vps.name == 'vps-cartorio'
    assert vps.role == 'admin'


def test_default_peers_count_and_roles() -> None:
    assert len(DEFAULT_PEERS) >= 1
    roles = {p.role for p in DEFAULT_PEERS}
    assert 'admin' in roles
    for p in DEFAULT_PEERS:
        assert p.ip.startswith('100.')
        assert p.name
        assert p.role


def test_is_ssh_source_allowed_vps() -> None:
    assert is_ssh_source_allowed('100.99.172.84') is True


def test_is_ssh_source_allowed_macbook() -> None:
    assert is_ssh_source_allowed('100.83.180.16') is True


def test_is_ssh_source_allowed_public_rejected() -> None:
    assert is_ssh_source_allowed('187.77.236.77') is False
    assert is_ssh_source_allowed('8.8.8.8') is False


def test_is_ssh_source_allowed_empty_and_garbage() -> None:
    assert is_ssh_source_allowed('') is False
    assert is_ssh_source_allowed('   ') is False
    assert is_ssh_source_allowed('not-an-ip') is False
    assert is_ssh_source_allowed('100.99') is False


def test_is_ssh_source_allowed_strips_port() -> None:
    assert is_ssh_source_allowed('100.99.172.84:22') is True


def test_is_ssh_source_allowed_custom_peers() -> None:
    peers = (AuthorizedPeer(name='lab', ip='100.1.2.3', role='ops'),)
    assert is_ssh_source_allowed('100.1.2.3', peers=peers) is True
    assert is_ssh_source_allowed('100.99.172.84', peers=peers) is False


def test_list_authorized_ips() -> None:
    s = list_authorized_ips()
    assert VPS_TAILSCALE_IP in s
    assert '187.77.236.77' not in s


def test_validate_sshd_ok() -> None:
    cfg = """
# drop-in
AllowUsers root
Match Address 100.64.0.0/10
    PasswordAuthentication no
"""
    r = validate_sshd_match_block(cfg)
    assert r.ok is True
    assert r.has_match_address_100 is True
    assert r.has_allow_users is True
    assert 'root' in r.allow_users


def test_validate_sshd_match_address_100_dot() -> None:
    cfg = 'AllowUsers root deploy\nMatch Address 100.99.172.0/24\n'
    r = validate_sshd_match_block(cfg)
    assert r.ok is True
    assert r.has_match_address_100 is True
    assert set(r.allow_users) == {'root', 'deploy'}


def test_validate_sshd_missing_match() -> None:
    r = validate_sshd_match_block('AllowUsers root\n')
    assert r.ok is False
    assert r.has_match_address_100 is False
    assert r.has_allow_users is True


def test_validate_sshd_missing_allow_users() -> None:
    r = validate_sshd_match_block('Match Address 100.64.0.0/10\n')
    assert r.ok is False
    assert r.has_match_address_100 is True
    assert r.has_allow_users is False


def test_validate_sshd_empty() -> None:
    r = validate_sshd_match_block('')
    assert r.ok is False
    assert 'empty' in r.detail


def test_validate_sshd_public_only_match_fails() -> None:
    cfg = 'AllowUsers root\nMatch Address 203.0.113.0/24\n'
    r = validate_sshd_match_block(cfg)
    assert r.ok is False
    assert r.has_match_address_100 is False


def test_inventory_report() -> None:
    rep = inventory_report()
    assert rep['vps_tailscale_ip'] == VPS_TAILSCALE_IP
    assert rep['count'] == len(DEFAULT_PEERS)
    assert VPS_TAILSCALE_IP in rep['authorized_ips']


def test_recommended_snippet_has_markers() -> None:
    snip = recommended_sshd_snippet()
    assert 'AllowUsers' in snip
    assert 'Match Address 100.' in snip
    assert VPS_TAILSCALE_IP in snip
