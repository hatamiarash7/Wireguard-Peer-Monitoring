"""Actions module for WireGuard events."""

from re import Match

from loguru import logger as log

from monitoring import REDIS


def check_peer(event: str, result: Match[str] | None) -> None:
    """Check peer's information and update Redis

    Args:
        event (str): Event's type
        result (Match[str] | None): Parsed event from kernel
    """

    REDIS.save_peer(
        peer_id=result.group(1),
        ip=result.group(2),
        port=result.group(3),
    )
    log.debug(
        f"[WG] {event}: Peer {result.group(1)} = {result.group(2)} : {result.group(3)}"
    )


def keepalive(event: str, result: Match[str] | None) -> None:
    """Update peer's keepalive status

    Args:
        event (str): Event's type
        result (Match[str] | None): Parsed event from kernel
    """

    REDIS.save_keepalive(peer_id=result.group(1))
    log.debug(
        f"[WG] {event}: Peer {result.group(1)} = {result.group(2)} : {result.group(3)}"
    )
