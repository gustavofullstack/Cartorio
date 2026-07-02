"""Pacote de repositories do cartorio.

A19 SQUAD A: BaseRepository + (futuro) repositories especializados
(ClienteRepository, ProtocoloRepository, etc).

Re-exporta BaseRepository para import direto:
    from app.repositories import BaseRepository
"""

from app.repositories.base import BaseRepository

__all__ = ["BaseRepository"]
