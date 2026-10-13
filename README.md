# WireGuard Peer Monitoring

Monitor WireGuard peer endpoints, received handshakes, and keepalives using Linux kernel events. Store the latest activity in Redis, send endpoint-change webhooks, and expose Prometheus metrics.

## How monitoring works

```text
WireGuard kernel dynamic-debug messages
    → rsyslog → UDP listener → interface/event parser
    → atomic Redis update → Prometheus counters and last-event gauges
                          → bounded queue → HTTP webhook worker
```

The service processes **received handshake initiation**, **received handshake response**, and **received keepalive packet** messages for one configured interface. IPv4 and bracketed IPv6 endpoints are supported. A new peer or a changed IP/port triggers a webhook, including changes first observed in a keepalive.

Each event compares and updates the Redis hash atomically with a Lua script. After the script is cached, this takes one Redis round trip. The HTTP worker reuses connections and runs independently of UDP ingestion.

### What the data means

- Peer IDs are kernel-internal numeric IDs, **not public keys**. They can change or be reused after interfaces or peers are recreated.
- Timestamps record when this service processes an event, in UTC. A received handshake message does not prove a completed handshake; this is not a replacement for `wg show`'s latest-handshake or transfer statistics.
- An inactive peer emits no events. Missing keepalives do not prove it is offline: WireGuard sends them only when needed or when persistent keepalive is configured.
- The service observes logs; it does not configure WireGuard, inspect tunnel traffic, or require privileged container access.

## Prerequisites

- A Linux WireGuard host with dynamic-debug support and `debugfs` mounted at `/sys/kernel/debug`.
- rsyslog reading kernel messages, usually through `imklog` or the system journal.
- Redis and either Docker Compose or Python 3.10+ with Poetry 2.4.3. Development and images use the Python patch version in `.python-version`.

## Quick start with Docker Compose

1. Create the configuration:

   ```bash
   cp config.toml.example config.toml
   ```

   Edit `config.toml`: set `[wireguard].interface` to your interface, `[redis].host` to `"redis"`, and `[manager].url` to your webhook URL (or `""` to disable delivery). Set `[app].host` and `[app].metrics_host` to `"0.0.0.0"` inside the container. Review all example values before use.

2. Build and start the services:

   ```bash
   docker compose up -d --build
   docker compose logs -f monitoring
   curl --fail http://127.0.0.1:9998/metrics
   ```

   Compose builds the current checkout, waits for Redis health, and persists Redis AOF data in the `redisdata` volume at `/data`. The application runs as UID/GID `10001`, with a read-only filesystem and configuration mount. Ensure that UID can read the mounted file.

3. Enable WireGuard debug logging on the **host**:

   ```bash
   echo 'module wireguard +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
   ```

   If the control file is absent, check the kernel's dynamic-debug support and debugfs mount. Debug logging must be re-enabled after reboot unless you configure host persistence.

4. Add this rule to `/etc/rsyslog.d/99-wireguard.conf`:

   ```text
   if $syslogfacility-text == 'kern' and $msg contains 'wireguard:' then {
       action(type="omfwd" target="127.0.0.1" port="9999" protocol="udp")
   }
   ```

   Validate and reload rsyslog:

   ```bash
   sudo rsyslogd -N1
   sudo systemctl restart rsyslog
   ```

   This rule relies on your kernel log format containing `wireguard:`. Check `sudo journalctl -k -f` while a peer connects; adapt the filter to the actual messages if necessary. The parser itself requires the exact configured interface followed by a colon and a space.

To disable the extra kernel logging:

```bash
echo 'module wireguard -p' | sudo tee /sys/kernel/debug/dynamic_debug/control
```

### Published image

For an existing Redis deployment, mount your configuration and run a published image:

```bash
docker run -d --name wg-peer-monitoring --restart unless-stopped \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --mount type=bind,src="$(pwd)/config.toml",dst=/app/config.toml,readonly \
  -p 127.0.0.1:9999:9999/udp -p 127.0.0.1:9998:9998 \
  hatamiarash7/wg-peer-monitoring:latest
```

Use a release tag for reproducible deployments. Inside a container, `localhost` refers to that container; configure a Redis hostname reachable from its network. Release builds target `linux/amd64` and `linux/arm64`.

### Local development

```bash
poetry env use python3.14
make dev
cp config.toml.example config.toml
# Configure a reachable Redis server, interface, and optional webhook.
CONFIG_FILE=config.toml make run
```

`python -m monitoring` and the installed `wg-peer-monitoring` command are equivalent entry points. Imports do not load configuration, open sockets, or start threads.

## Configuration

The TOML file is validated before startup. Missing options use defaults; unknown sections/options, wrong types, invalid ports, and malformed webhook URLs produce a nonzero exit status.

| Environment variable | Purpose                                             | Default                       |
| -------------------- | --------------------------------------------------- | ----------------------------- |
| `CONFIG_FILE`        | TOML file path                                      | `/app/config.toml`            |
| `LOG_LEVEL`          | Loguru level, such as `DEBUG`, `INFO`, or `WARNING` | `INFO`                        |
| `ENV`                | Enables colored logs when set to `local`            | `local` (image: `production`) |
| `APP_VERSION`        | Release version override for image metadata/metrics | Installed package version     |

| TOML option                             | Default              | Purpose                                                          |
| --------------------------------------- | -------------------- | ---------------------------------------------------------------- |
| `app.host` / `app.port`                 | `127.0.0.1` / `9999` | UDP bind address/port; IPv6 literal addresses also work          |
| `app.metrics_host` / `app.metrics_port` | `127.0.0.1` / `9998` | Prometheus listener                                              |
| `wireguard.interface`                   | `wg0`                | Exact interface name to monitor                                  |
| `redis.host` / `redis.port`             | `localhost` / `6379` | Redis connection                                                 |
| `redis.db`                              | `3`                  | Redis database index                                             |
| `redis.username` / `redis.password`     | `default` / empty    | Redis credentials                                                |
| `redis.socket_timeout`                  | `2.0`                | Redis connect/read timeout in seconds                            |
| `manager.url`                           | empty                | HTTP(S) webhook URL; empty disables notifications                |
| `manager.timeout`                       | `5.0`                | HTTP connect/read/write/pool timeout in seconds                  |
| `manager.retries`                       | `3`                  | Extra attempts after the first request                           |
| `manager.retry_delay`                   | `0.5`                | Initial exponential retry delay in seconds, capped at 30 seconds |
| `manager.queue_size`                    | `1000`               | Maximum queued notifications                                     |
| `manager.shutdown_timeout`              | `10.0`               | Maximum wait for the webhook worker during shutdown              |

The example uses wildcard app listeners for Docker. Compose publishes both ports only on host loopback. For a remote rsyslog sender or Prometheus server, change the port mappings deliberately and restrict access to trusted senders: UDP messages are unauthenticated.

## Redis data and webhook contract

Hashes retain the existing key format, `wireguard_peer:{peer_id}`:

```text
wireguard_peer:12
  ip         192.0.2.10
  port       51820
  handshake  2026-10-13 12:00:00
  keepalive  2026-10-13 12:00:25
```

The `handshake` and `keepalive` fields are created when that event is observed; one does not overwrite the other. IPv6 addresses are stored without brackets. Hashes have no TTL and survive application restarts when Redis persistence is enabled.

Inspect a peer in Compose:

```bash
docker compose exec redis redis-cli -n 3 HGETALL wireguard_peer:12
```

A new or changed endpoint queues an HTTP POST with JSON:

```json
{"peer": "192.0.2.10:51820"}
```

IPv6 payloads use `{"peer": "[2001:db8::10]:51820"}`. The receiver should accept duplicate notifications. Successful `2xx` responses complete delivery; network errors, `408`, `429`, and `5xx` responses are retried. Other HTTP errors and redirects are not retried or followed.

### Delivery and lifecycle limits

- UDP, kernel logging, and rsyslog can drop or rate-limit messages. This is best-effort observation, not an audit log.
- Redis is checked at startup. Later Redis failures drop the affected event and increment an error counter; subsequent datagrams continue to be processed. Redis operations remain synchronous and are bounded by socket timeouts.
- Notifications are queued **after** persistence. The queue is bounded and memory-only: overflow, exhausted retries, process failure, or shutdown can lose notifications. An unchanged endpoint does not requeue a failed notification. There is no transactional outbox or exactly-once guarantee.
- `SIGINT`, `SIGTERM`, and `SIGHUP` request shutdown. Queued webhooks are discarded, retry waits are interrupted, and an in-flight request gets up to the configured shutdown timeout. SIGHUP does not reload configuration.
- One process monitors one interface. Give independent hosts/interfaces separate Redis databases to prevent numeric peer-ID collisions.
- Peer hashes and per-peer metric series remain until explicitly cleared or the process restarts (metrics only). Long-lived deployments with frequent peer recreation should plan retention and cardinality management.

## Prometheus monitoring

Scrape `http://127.0.0.1:9998/metrics`. The container healthcheck probes the configured metrics socket; it indicates listener liveness, not Redis readiness or webhook delivery.

| Metric                                               | Labels          | Meaning                                                 |
| ---------------------------------------------------- | --------------- | ------------------------------------------------------- |
| `wg_peer_monitoring_app_version_info`                | `version`       | Application release                                     |
| `wg_peer_monitoring_wg_wireguard_events_total`       | `peer`, `event` | Successfully stored events (`Handshake` or `Keepalive`) |
| `wg_peer_monitoring_wg_peer_changes_total`           | `peer`          | New or changed endpoints                                |
| `wg_peer_monitoring_wg_last_event_timestamp_seconds` | `peer`, `event` | Last successfully stored event, Unix seconds            |
| `wg_peer_monitoring_errors_total`                    | `reason`        | `encoding`, `endpoint`, or `redis` failures             |
| `wg_peer_monitoring_notifications_total`             | `result`        | `delivered`, `failed`, or `dropped` notifications       |

Prometheus also emits counter `_created` samples. These are the **creation times of counter series**, not the times of the latest events. Counters reset on restart; last-event gauges become available after a matching event.

Example scrape configuration for Prometheus on the same host:

```yaml
scrape_configs:
  - job_name: wireguard-peer-monitoring
    static_configs:
      - targets: ["127.0.0.1:9998"]
```

Useful PromQL:

```promql
sum by (event) (rate(wg_peer_monitoring_wg_wireguard_events_total[5m]))
time() - wg_peer_monitoring_wg_last_event_timestamp_seconds{event="Keepalive"}
sum(rate(wg_peer_monitoring_errors_total[5m]))
sum(increase(wg_peer_monitoring_notifications_total{result=~"failed|dropped"}[15m]))
```

### Verify the pipeline without a live peer

With the service running, send a synthetic message (replace `wg0` with your configured interface). This writes peer `12` and may trigger your configured webhook:

```bash
python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.sendto(
        b"wg0: Receiving handshake initiation from peer 12 (192.0.2.10:51820)",
        ("127.0.0.1", 9999),
    )
PY

curl --fail http://127.0.0.1:9998/metrics
```

If synthetic events work but live events do not, check kernel logging, rsyslog's input/filter, the interface name, and UDP routing. If startup fails, check config readability, Redis reachability, and port conflicts. Inspect application logs and the error/notification counters for runtime failures.

## Testing and contributing

```bash
make dev
make check       # formatting, imports, pylint, tests, coverage, Bandit, lockfile
make format      # apply Black/isort formatting
make build       # wheel and source distribution
make docker-build
```

Tests use pytest, isolated Prometheus registries, HTTP mocks, and fakeredis with Lua support. They exercise parsing, IPv6, endpoint changes, configuration errors, retries, queue overflow, shutdown, and partial startup failures without external services. `make test` enforces **95% combined line/branch coverage** and writes `coverage.xml`.

CI runs checks on Python 3.10 and the pinned development version and builds the runtime image. Published GitHub releases first run CI, scan an amd64 candidate with Trivy, then publish amd64/arm64 images with SBOM/provenance metadata. Fixable high/critical findings block publication. Configure the `DOCKER_PASSWORD` repository secret with a Docker Hub access token. Prereleases receive their release tag; only stable releases update `latest`. Actions are pinned to commit SHAs and updated by Dependabot.

To support another event, add a compiled pattern and action callable to `monitoring/handler.py`'s `EVENTS`. Capture groups must provide peer ID, IP, and port; add behavior and error-path tests. Other kernel messages—sent packets, cookie responses, retransmissions, peer creation/destruction, invalid packets, and key rotation—are currently ignored.

Open an issue with reproduction steps or submit a pull request describing the change and verification performed. Keep real configuration and credentials out of tests and commits.

## License and support

[MIT](LICENSE), copyright Arash Hatami.

You can support development through [PayPing](https://payping.ir/@hatamiarash7), [Bitcoin](https://donatebadges.ir/donate/Bitcoin/bc1qmmh6vt366yzjt3grjxjjqynrrxs3frun8gnxrz), or [Ethereum](https://donatebadges.ir/donate/Ethereum/0x0831bD72Ea8904B38Be9D6185Da2f930d6078094).
