"""Event handler for WireGuard kernel messages."""

import re

from monitoring import CONFIG, action, prom

# All kernel messages with the Wireguard's interface name
WG_LOG = re.compile(rf"{CONFIG.get('wireguard', 'interface')}: (.*)$")

# Events to be handled
EVENTS = [
    {
        # Handshake messages like `Receiving handshake initiation|response`
        "name": "Handshake",
        "pattern": re.compile(
            r"Receiving handshake [a-z]* from peer (\d) \((.*):(.*)\)$"
        ),
        "action": "check_peer",
    },
    {
        # Keepalive messages
        "name": "Keepalive",
        "pattern": re.compile(
            r"Receiving keepalive packet from peer (\d) \((.*):(.*)\)$"
        ),
        "action": "keepalive",
    },
]


def parse(data: str) -> None:
    """Parse event's message and call the respective action."""

    wg_match = WG_LOG.search(data)
    if wg_match:
        message = wg_match.group(1)

        for event in EVENTS:
            result = event["pattern"].search(message)
            if result:
                getattr(action, event["action"])(event["name"], result)
                prom.WG_EVENTS.labels(result.group(1), event["name"]).inc()
