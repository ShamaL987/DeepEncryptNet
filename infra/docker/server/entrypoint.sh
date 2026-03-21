#!/bin/bash
set -euo pipefail

mkdir -p /data/files /data/logs /data/runtime

exec /app/.venv/bin/python -m uvicorn app.main:application --host 0.0.0.0 --port 8000