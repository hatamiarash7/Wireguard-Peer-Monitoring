from re import Match

from loguru import logger as log

from monitoring import REDIS


def _check_peer(event: str, result: Match[str] | None):
    REDIS.save_peer(
        id=result.group(1),
        ip=result.group(2),
        port=result.group(3),
    )
    log.debug(
        f"[WG] {event}: Peer {result.group(1)} = {result.group(2)} : {result.group(3)}"
    )


def _keepalive(event: str, result: Match[str] | None):
    REDIS.save_keepalive(id=result.group(1))
    log.debug(
        f"[WG] {event}: Peer {result.group(1)} = {result.group(2)} : {result.group(3)}"
    )
