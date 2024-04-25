import socket
import sys

from loguru import logger as log

from monitoring import CONFIG, handler, utils

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
        handler.parse(data.decode())


if __name__ == "__main__":
    main()
