import re
import socket
import sys

from loguru import logger as log

from monitoring import CONFIG, utils

WG_LOG_PATTERN = re.compile(rf"{CONFIG.get('wireguard', 'interface')}: (.*)$")
message_pattern = re.compile(
    r"Receiving handshake [a-z]* from peer (\d) \((.*):(.*)\)$"
)

UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _signal_handler(sig, _):
    print("Received signal {}, closing socket...".format(sig))
    UDP_SOCKET.close()
    sys.exit(0)


def main() -> None:
    log.info(
        "[APP] Starting Wireguard Peer Monitoring",
        Server=CONFIG.get("wireguard", "interface"),
    )

    UDP_SOCKET.bind(
        (
            utils.get_env("UDP_IP", "0.0.0.0"),
            utils.get_env("UDP_PORT", 9999),
        )
    )

    while True:
        data, _ = UDP_SOCKET.recvfrom(1024)

        try:
            wg_match = WG_LOG_PATTERN.search(data.decode())
            if wg_match:
                message = wg_match.group(1)

                msg_match = message_pattern.search(message)
                if msg_match:
                    log.info(
                        f"[WG] Peer {msg_match.group(1)} = {msg_match.group(2)} : {msg_match.group(3)}"
                    )
        except Exception as e:
            log.error("[UDP] Error processing data:", e)


if __name__ == "__main__":
    main()
