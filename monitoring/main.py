"""Application lifecycle and resilient UDP ingestion."""

import signal
import socket
import threading
from contextlib import ExitStack

from loguru import logger as log
from prometheus_client import start_http_server
from redis.exceptions import RedisError

from monitoring import __version__
from monitoring.config import ConfigError, ConfigManager
from monitoring.handler import Handler
from monitoring.notifier import JobManager
from monitoring.prom import Metrics
from monitoring.redis_handler import Redis
from monitoring.utils import configure_logging, get_env


def receive(
    udp_socket: socket.socket, handler: Handler, stopped: threading.Event
) -> None:
    """Read complete UDP datagrams; malformed input and Redis outages are isolated."""
    while not stopped.is_set():
        try:
            data, _ = udp_socket.recvfrom(65535)
        except socket.timeout:
            continue
        try:
            handler.parse(data.decode("utf-8"))
        except UnicodeDecodeError:
            handler.metrics.errors.labels("encoding").inc()
        except RedisError:
            handler.metrics.errors.labels("redis").inc()
            log.error("[REDIS] Event could not be stored")


def run(config: ConfigManager, stopped: threading.Event) -> None:
    """Start dependencies in order and release them on every exit path."""
    metrics = Metrics()
    metrics.app_info.info({"version": __version__})
    with ExitStack() as resources:
        notifier = JobManager(config, metrics)
        store = Redis(config, notifier, metrics)
        resources.callback(store.close)
        store.ping()
        resources.callback(notifier.stop)
        notifier.start()
        host = config.get("app", "host")
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        udp_socket = resources.enter_context(socket.socket(family, socket.SOCK_DGRAM))
        udp_socket.settimeout(0.5)
        udp_socket.bind((host, config.get("app", "port")))
        server, thread = start_http_server(
            config.get("app", "metrics_port"),
            addr=config.get("app", "metrics_host"),
            registry=metrics.registry,
        )
        resources.callback(thread.join)
        resources.callback(server.server_close)
        resources.callback(server.shutdown)
        log.info(
            "[APP] Monitoring {} on {}:{} ({})",
            config.get("wireguard", "interface"),
            host,
            config.get("app", "port"),
            __version__,
        )
        receive(
            udp_socket,
            Handler(config.get("wireguard", "interface"), store, metrics),
            stopped,
        )


def main() -> int:
    """CLI entry point with cooperative signal handling and a useful exit status."""
    stopped = threading.Event()
    previous = {}
    try:
        configure_logging()
        config = ConfigManager(get_env("CONFIG_FILE", "/app/config.toml"))
        config.load()
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[sig] = signal.signal(sig, lambda *_: stopped.set())
        run(config, stopped)
    except (ConfigError, OSError, RedisError, ValueError) as exc:
        log.error("[APP] {}", exc)
        return 1
    finally:
        for sig, original in previous.items():
            signal.signal(sig, original)
    return 0
