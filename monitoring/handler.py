"""Parse supported messages for exactly one WireGuard interface."""

import re
from ipaddress import ip_address

from monitoring import action
from monitoring.prom import Metrics
from monitoring.redis_handler import Redis

ENDPOINT = r"peer (\d+) \((\[[^\]\s]+\]|[^():\s]+):(\d{1,5})\)"
EVENTS = (
    (
        "Handshake",
        re.compile(r"Receiving handshake (?:initiation|response) from " + ENDPOINT),
        action.check_peer,
    ),
    (
        "Keepalive",
        re.compile(r"Receiving keepalive packet from " + ENDPOINT),
        action.keepalive,
    ),
)


class Handler:  # pylint: disable=too-few-public-methods
    """Precompile interface matching and inject storage and metrics explicitly."""

    def __init__(self, interface: str, store: Redis, metrics: Metrics):
        self.pattern = re.compile(rf"(?<![\w.:-]){re.escape(interface)}: (.*)$")
        self.store = store
        self.metrics = metrics

    def parse(self, data: str) -> bool:
        """Return whether a supported event was stored; reject malformed endpoints."""
        wg_match = self.pattern.search(data.rstrip())
        if not wg_match:
            return False
        for name, pattern, callback in EVENTS:
            result = pattern.fullmatch(wg_match.group(1))
            if result:
                try:
                    ip_address(result.group(2).strip("[]"))
                    if not 1 <= int(result.group(3)) <= 65535:
                        raise ValueError("Invalid endpoint port")
                except ValueError:
                    self.metrics.errors.labels("endpoint").inc()
                    return False
                callback(self.store, result)
                self.metrics.events.labels(result.group(1), name).inc()
                self.metrics.last_event.labels(
                    result.group(1), name
                ).set_to_current_time()
                return True
        return False
