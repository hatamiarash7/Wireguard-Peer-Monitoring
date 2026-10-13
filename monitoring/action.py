"""Storage actions for supported WireGuard events."""

from re import Match

from monitoring.redis_handler import Redis


def check_peer(store: Redis, result: Match[str]) -> None:
    """Record a handshake and check for endpoint changes."""
    store.save_peer(*result.groups())


def keepalive(store: Redis, result: Match[str]) -> None:
    """Record a keepalive, including endpoint roaming between handshakes."""
    store.save_keepalive(*result.groups())
