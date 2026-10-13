"""Instance-owned Prometheus collectors, isolated from import-time state."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Info

NS = "wg_peer_monitoring"


class Metrics:  # pylint: disable=too-few-public-methods
    """Application metrics; every runtime gets its own registry."""

    def __init__(self):
        self.registry = CollectorRegistry()
        options = {"namespace": NS, "registry": self.registry}
        self.app_info = Info("app_version", "Application version", **options)
        self.events = Counter(
            "wg_wireguard_events",
            "Successfully stored WireGuard events",
            ["peer", "event"],
            **options,
        )
        self.peer_changes = Counter(
            "wg_peer_changes",
            "New or changed endpoints",
            ["peer"],
            **options,
        )
        self.last_event = Gauge(
            "wg_last_event_timestamp_seconds",
            "Last stored event (Unix seconds)",
            ["peer", "event"],
            **options,
        )
        self.errors = Counter(
            "errors",
            "Rejected datagrams or failed storage operations",
            ["reason"],
            **options,
        )
        self.notifications = Counter(
            "notifications",
            "Webhook outcomes",
            ["result"],
            **options,
        )
