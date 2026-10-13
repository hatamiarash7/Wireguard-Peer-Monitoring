ARG PYTHON_VERSION=3.14.4
FROM python:${PYTHON_VERSION}-slim AS builder

ARG POETRY_VERSION=2.4.3
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1
WORKDIR /app

# BuildKit keeps this cache outside the resulting image.
# hadolint ignore=DL3042
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "poetry==${POETRY_VERSION}"
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry sync --only main --no-root
COPY README.md LICENSE ./
COPY monitoring ./monitoring
RUN poetry build --format wheel \
    && .venv/bin/pip install --no-deps dist/*.whl

FROM python:${PYTHON_VERSION}-slim AS runtime
ARG APP_VERSION=""
ARG DATE_CREATED
ARG VCS_REF
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    CONFIG_FILE=/app/config.toml \
    ENV=production \
    APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="wireguard-peer-monitoring" \
    org.opencontainers.image.description="Monitor WireGuard peers using kernel events" \
    org.opencontainers.image.source="https://github.com/hatamiarash7/Wireguard-Peer-Monitoring" \
    org.opencontainers.image.version="${APP_VERSION}" \
    org.opencontainers.image.created="${DATE_CREATED}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.licenses="MIT"
WORKDIR /app
RUN groupadd --gid 10001 monitoring \
    && useradd --uid 10001 --gid monitoring --no-create-home --shell /usr/sbin/nologin monitoring
COPY --from=builder /app/.venv /app/.venv
USER 10001:10001
EXPOSE 9999/udp 9998/tcp
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-m", "monitoring.healthcheck"]
CMD ["python", "-m", "monitoring"]
