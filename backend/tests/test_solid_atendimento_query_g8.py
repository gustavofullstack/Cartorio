"""G8.11.T1 tests.

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

from app.services.solid_atendimento_query import AtendimentoQueryService, AtendimentoRow


def _sample() -> AtendimentoQueryService:
    return AtendimentoQueryService(
        [
            AtendimentoRow('1', 'open', 'telegram'),
            AtendimentoRow('2', 'concluido', 'whatsapp'),
            AtendimentoRow('3', 'pending', 'telegram'),
        ]
    )


def test_list_open() -> None:
    svc = _sample()
    open_ = svc.list_open('open')
    assert len(open_) == 2
    assert all(r.status in {'open', 'pending'} for r in open_)


def test_list_closed() -> None:
    svc = _sample()
    closed = svc.list_open('closed')
    assert len(closed) == 1
    assert closed[0].id == '2'


def test_all() -> None:
    assert len(_sample().list_open('all')) == 3


def test_count_by_canal() -> None:
    c = _sample().count_by_canal()
    assert c['telegram'] == 2
    assert c['whatsapp'] == 1


def test_api_payload() -> None:
    p = _sample().as_api_payload('open')
    assert p['count'] == 2
    assert 'items' in p
