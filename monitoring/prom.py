from prometheus_client import Counter, Info

NS = "wg_peer_monitoring"

APP_INFO = Info(
    namespace=NS,
    subsystem="app",
    name="version",
    documentation="Application information",
)

WG_EVENTS = Counter(
    namespace=NS,
    subsystem="app",
    name="wireguard_events",
    documentation="Wireguard events",
    labelnames=["peer", "event"],
)
