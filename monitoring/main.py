"""Main module"""

import socket
import sys

from loguru import logger as log

from monitoring import CONFIG, NOTIFIER, __version__, handler, utils

UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _signal_handler(sig, _) -> None:
    """OS signal handler"""

    log.info(f"[APP] Received signal {sig}, Exit ...")
    UDP_SOCKET.close()
    NOTIFIER.stop()
    sys.exit(0)


def main() -> None:
    """Main function"""

    UDP_HOST = utils.get_env("UDP_HOST", CONFIG.get("app", "host"))
    UDP_PORT = utils.get_env("UDP_PORT", CONFIG.get("app", "port"))

    log.info(
        "[APP] Starting app",
        Interface=CONFIG.get("wireguard", "interface"),
        Version=__version__,
        Host=UDP_HOST,
        PORT=UDP_PORT,
    )

    UDP_SOCKET.bind((UDP_HOST, UDP_PORT))

    while True:
        data, _ = UDP_SOCKET.recvfrom(1024)
        handler.parse(data.decode())


if __name__ == "__main__":
    main()
