"""Atomic peer updates using one Redis round trip per event."""

from datetime import datetime, timezone
from ipaddress import ip_address

import redis
from loguru import logger as log
from redis.backoff import NoBackoff
from redis.retry import Retry

from monitoring.config import ConfigManager
from monitoring.prom import Metrics

# Compare and write on the server so concurrent events cannot lose endpoint changes.
UPDATE_PEER = """
local old_ip = redis.call('HGET', KEYS[1], 'ip')
local old_port = redis.call('HGET', KEYS[1], 'port')
local changed = old_ip ~= ARGV[1] or old_port ~= ARGV[2]
redis.call('HSET', KEYS[1], 'ip', ARGV[1], 'port', ARGV[2], ARGV[3], ARGV[4])
if changed then return 1 else return 0 end
"""


class Redis:
    """Own a Redis connection pool and persist peer activity before notifying."""

    def __init__(self, config: ConfigManager, notifier, metrics: Metrics):
        self.config = config
        self.notifier = notifier
        self.metrics = metrics
        self.redis_client = redis.Redis(
            **{
                key: config.get("redis", key)
                for key in (
                    "host",
                    "port",
                    "db",
                    "username",
                    "password",
                    "socket_timeout",
                )
            },
            socket_connect_timeout=config.get("redis", "socket_timeout"),
            retry=Retry(NoBackoff(), 0),
            health_check_interval=30,
            client_name="wireguard-peer-monitoring",
        )
        self._update_peer = self.redis_client.register_script(UPDATE_PEER)

    def save_peer(self, peer_id: str, ip: str, port: str) -> None:
        """Record a received handshake."""
        self._save_event(peer_id, ip, port, "handshake")

    def save_keepalive(self, peer_id: str, ip: str, port: str) -> None:
        """Record a received keepalive and its endpoint."""
        self._save_event(peer_id, ip, port, "keepalive")

    def _save_event(self, peer_id: str, ip: str, port: str, event: str) -> None:
        address = ip_address(ip.strip("[]"))
        ip = str(address)
        port = str(int(port))
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        changed = self._update_peer(
            keys=[f"wireguard_peer:{peer_id}"],
            args=[ip, port, event, timestamp],
        )
        if changed:
            self.metrics.peer_changes.labels(peer_id).inc()
            log.info("[WG] Endpoint changed for peer {}: {}:{}", peer_id, ip, port)
            url = self.config.get("manager", "url")
            if url:
                endpoint = f"[{ip}]:{port}" if address.version == 6 else f"{ip}:{port}"
                self.notifier.add_job({"url": url, "payload": {"peer": endpoint}})

    def get_peer(self, peer_id: str) -> dict:
        """Return the stored hash with byte keys and values."""
        return self.redis_client.hgetall(f"wireguard_peer:{peer_id}")

    def ping(self) -> None:
        """Check Redis connectivity during startup."""
        self.redis_client.ping()

    def close(self) -> None:
        """Release the owned connection pool."""
        self.redis_client.close()
