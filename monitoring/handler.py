import re

from loguru import logger as log

from monitoring import CONFIG, action

# All kernel messages with the Wireguard's interface name
WG_LOG = re.compile(rf"{CONFIG.get('wireguard', 'interface')}: (.*)$")

EVENTS = [
    {
        # Handshake messages like `Receiving handshake initiation|response`
        "name": "Handshake",
        "pattern": re.compile(
            r"Receiving handshake [a-z]* from peer (\d) \((.*):(.*)\)$"
        ),
        "action": "_check_peer",
    },
]


def parse(data: str):
    wg_match = WG_LOG.search(data)
    if wg_match:
        message = wg_match.group(1)

        for event in EVENTS:
            log.debug(f"[WG] New event: {event['name']}")
            result = event["pattern"].search(message)
            if result:
                getattr(action, event["action"])(result)
