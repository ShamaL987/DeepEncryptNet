FROM node:20-alpine AS frontend-build
WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:${PATH}"
ENV APP_ENV=docker
ENV CONFIG_PATH=/app/config.docker.yaml
ENV FLOW_BASE_DIR=/data/files

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-client \
    postgresql-contrib \
    supervisor \
    curl \
    ca-certificates \
    bash \
    && rm -rf /var/lib/apt/lists/*

ENV POSTGRES_DB=flows
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV PGDATA=/var/lib/postgresql/data

VOLUME ["/var/lib/postgresql/data"]

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen

COPY config.docker.yaml /app/config.docker.yaml
COPY config.local.yaml /app/config.local.yaml

COPY app ./app

COPY --from=frontend-build /frontend/dist /app/app/static/dashboard

COPY supervisord.conf /etc/supervisor/conf.d/deepencryptnet.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
EXPOSE 5432

ENTRYPOINT ["/entrypoint.sh"]
