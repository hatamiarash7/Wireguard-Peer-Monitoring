# Repository guidance

## Verification

- Use the Python version in `.python-version` and Poetry 2.4.3 (also used by Docker and CI).
- Install with `make dev`, then run `make check`. Tests enforce 95% line/branch coverage and run without Redis or external webhooks.
- When changing the Redis Lua script, run the tests against fakeredis with its Lua extra, and smoke-test with real Redis if Docker is available.
- See README.md for deployment, kernel logging, configuration, and the delivery guarantees.

## Runtime boundaries

- Imports are side-effect-free. `main.main()` loads configuration and handles signals; `main.run()` owns resources through an ExitStack. Keep new sockets, threads, and clients inside this lifecycle.
- `Handler`, `Redis`, and `JobManager` receive dependencies explicitly. Each runtime owns a `Metrics` registry; tests can instantiate these classes independently.
- Add supported events to `handler.EVENTS` with a compiled regex and an action callable. Capture groups are peer ID, IP, and port. Metrics increment only after successful persistence.
- Redis keys remain `wireguard_peer:{peer_id}` and timestamps remain UTC `YYYY-MM-DD HH:MM:SS`. The Lua script compares and writes the endpoint atomically. Preserve byte keys/values returned by `get_peer()`.
- Both handshakes and keepalives detect endpoint changes. Webhooks retain `{"peer": "ip:port"}`; IPv6 endpoints use brackets.
- Webhook delivery is bounded and best-effort. Shutdown cancels queued work and retries; never block UDP ingestion waiting for queue space.
- Treat `config.toml` and locally modified example values as user data. Tests must use isolated configuration and HTTP mocks.
