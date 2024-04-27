"""Main module"""

import socket
import sys

from loguru import logger as log
from prometheus_client import start_http_server as prometheus_server

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

    METRICS_HOST = utils.get_env("METRICS_HOST", CONFIG.get("app", "metrics_host"))
    METRICS_PORT = utils.get_env("METRICS_PORT", CONFIG.get("app", "metrics_port"))

    log.info(
        "[APP] Starting metrics",
        Host=METRICS_HOST,
        Port=METRICS_PORT,
    )
    prometheus_server(
        addr=METRICS_HOST,
        port=METRICS_PORT,
    )

    while True:
        data, _ = UDP_SOCKET.recvfrom(1024)
        handler.parse(data.decode())


if __name__ == "__main__":
    main()
