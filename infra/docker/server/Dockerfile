FROM node:20-alpine AS frontend-build
WORKDIR /frontend

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./
RUN yarn build


FROM python:3.12-slim-bookworm AS python-builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_DEV=1
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,id=s/<RAILWAY_SERVICE_ID>-/root/.cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable

COPY app ./app
RUN --mount=type=cache,id=s/<RAILWAY_SERVICE_ID>-/root/.cache/uv,target=/root/.cache/uv \
    uv sync --frozen --no-editable


FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"
ENV APP_ENV=server
ENV CONFIG_PATH=/app/app/config.server.yaml
ENV FLOW_BASE_DIR=/data/files

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /app/.venv /app/.venv
COPY --from=python-builder /app/app /app/app
COPY --from=frontend-build /frontend/dist /app/app/static/dashboard

COPY infra/docker/server/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /data/files /data/logs /data/runtime

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]