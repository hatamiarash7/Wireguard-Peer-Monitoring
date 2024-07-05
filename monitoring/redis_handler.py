"""Redis handler module"""

from datetime import datetime, timezone
from typing import Awaitable, Union

import redis
from loguru import logger as log

from monitoring import prom


class Redis:
    """This class will handle Redis connection and jobs"""

    def __init__(
        self,
        config,
        notifier,
        host: str,
        port: int,
        db: int,
        password: str,
        username: str = "default",
    ):
        self.config = config
        self.notifier = notifier
        self.redis_client = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            username=username,
            client_name="wireguard-peer-monitoring",
        )

    def save_peer(
        self,
        peer_id: str,
        ip: str,
        port: str,
    ) -> None:
        """This function will save peer's information in Redis.

        Args:
            peer_id (str): Peer's ID
            ip (str): Peer's IP
            port (str): Peer's port
        """

        data = {"handshake": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        # Check if IP and port have changed
        existing_peer = self.get_peer(peer_id)
        if not (
            existing_peer
            and existing_peer.get(b"ip") == ip.encode()
            and existing_peer.get(b"port") == str(port).encode()
        ):
            data["ip"] = ip
            data["port"] = port
            log.warning(
                f"[WG] Endpoint's information changed for {peer_id} = {ip} : {port}"
            )
            prom.WG_PEER_CHANGE.labels(peer_id).inc()
            self.notifier.add_job(
                {
                    "url": self.config.get("manager", "url"),
                    "payload": {"peer": f"{ip}:{port}"},
                }
            )

        self.redis_client.hmset(f"wireguard_peer:{peer_id}", data)

    def get_peer(self, peer_id: str) -> Union[Awaitable[dict], dict]:
        """This function will get peer's information from Redis.

        Args:
            peer_id (str): Peer's ID

        Returns:
            Union[Awaitable[dict], dict]: Peer's information
        """

        return self.redis_client.hgetall(f"wireguard_peer:{peer_id}")

    def save_keepalive(self, peer_id: str) -> None:
        """Update keepalive timestamp in Redis.

        Args:
            peer_id (str): Peer's ID
        """

        data = {"keepalive": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        self.redis_client.hmset(f"wireguard_peer:{peer_id}", data)
