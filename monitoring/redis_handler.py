"""Redis handler module"""

from datetime import datetime, timezone
from typing import Awaitable, Union

import redis
from loguru import logger as log


class Redis:
    """This class will handle Redis connection and jobs"""

    def __init__(
        self,
        notifier,
        host: str,
        port: int,
        db: int,
        password: str,
        username: str = "default",
    ):
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
        id: str,
        ip: str,
        port: str,
    ) -> None:
        """This function will save peer's information in Redis.

        Args:
            id (str): Peer's ID
            ip (str): Peer's IP
            port (str): Peer's port
        """

        data = {"handshake": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        # Check if IP and port have changed
        existing_peer = self.get_peer(id)
        if not (
            existing_peer
            and existing_peer.get(b"ip") == ip.encode()
            and existing_peer.get(b"port") == str(port).encode()
        ):
            data["ip"] = ip
            data["port"] = port
            log.warning(f"[WG] Endpoint's information changed for {id} = {ip} : {port}")
            self.notifier.add_job(
                {
                    "url": "https://webhook.arash-hatami.ir/bf4aa44f-ce8d-40b4-929f-a53536e20479",
                    "payload": {"data": "example"},
                }
            )

        self.redis_client.hmset(f"wireguard_peer:{id}", data)

    def get_peer(self, id: str) -> Union[Awaitable[dict], dict]:
        """This function will get peer's information from Redis.

        Args:
            id (str): Peer's ID

        Returns:
            Union[Awaitable[dict], dict]: Peer's information
        """

        return self.redis_client.hgetall(f"wireguard_peer:{id}")

    def save_keepalive(self, id: str) -> None:
        """Update keepalive timestamp in Redis.

        Args:
            id (str): Peer's ID
        """

        data = {"keepalive": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        self.redis_client.hmset(f"wireguard_peer:{id}", data)
