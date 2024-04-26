from datetime import datetime, timezone

import redis
from loguru import logger as log


class Redis:
    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        password: str,
        username: str = "default",
    ):
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
        id,
        ip,
        port,
    ):
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
            log.debug(f"[WG] Endpoint's information changed for {id} = {ip} : {port}")

        self.redis_client.hmset(f"wireguard_peer:{id}", data)

    def get_peer(self, id):
        return self.redis_client.hgetall(f"wireguard_peer:{id}")

    def save_keepalive(self, id):
        data = {"keepalive": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        self.redis_client.hmset(f"wireguard_peer:{id}", data)
