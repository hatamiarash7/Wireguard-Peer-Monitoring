"""Container liveness probe using the configured metrics listener."""

import socket

from monitoring.config import ConfigManager
from monitoring.utils import get_env


def main() -> int:
    """Check that the metrics socket accepts connections."""
    config = ConfigManager(get_env("CONFIG_FILE", "/app/config.toml"))
    config.load()
    host = config.get("app", "metrics_host")
    # Translate wildcard listeners to loopback; this probe never binds a socket.
    host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(host, host)  # nosec B104
    with socket.create_connection((host, config.get("app", "metrics_port")), timeout=2):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
