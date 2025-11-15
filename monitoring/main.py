"""Main module"""

import socket
import sys

from loguru import logger as log
from prometheus_client import start_http_server as prometheus_server

from monitoring import CONFIG, NOTIFIER, __version__, handler, prom

UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
METRICS_SERVER = None
METRICS_THREAD = None


def _signal_handler(sig, _) -> None:
    """OS signal handler"""

    log.info(f"[APP] Received signal {sig}, Exit ...")

    # Close UDP socket
    UDP_SOCKET.close()

    # Stop job manager
    NOTIFIER.stop()

    # Stop metrics server
    METRICS_SERVER.shutdown()
    METRICS_THREAD.join()

    # Exit the app
    sys.exit(0)


def main() -> None:
    """Main function"""
    global METRICS_SERVER, METRICS_THREAD

    udp_host = CONFIG.get("app", "host")
    udp_port = CONFIG.get("app", "port")

    log.info(
        "[APP] Starting app",
        Interface=CONFIG.get("wireguard", "interface"),
        Version=__version__,
        Host=udp_host,
        PORT=udp_port,
    )

    UDP_SOCKET.bind((udp_host, udp_port))

    metrics_host = CONFIG.get("app", "metrics_host")
    metrics_port = CONFIG.get("app", "metrics_port")

    log.info(
        "[APP] Starting metrics",
        Host=metrics_host,
        Port=metrics_port,
    )
    METRICS_SERVER, METRICS_THREAD = prometheus_server(
        addr=metrics_host,
        port=metrics_port,
    )
    prom.APP_INFO.info({"version": __version__})

    while True:
        data, _ = UDP_SOCKET.recvfrom(1024)
        handler.parse(data.decode())


if __name__ == "__main__":
    main()
