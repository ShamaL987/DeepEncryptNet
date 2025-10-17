# DeepEncryptNet Backend (skeleton)

Backend-only container that tails a CSV, detects HTTPS flow starts, shards to a bounded worker pool, closes flows on FIN/idle/active/max, writes per-flow files, and indexes them in SQLite. Exposes FastAPI endpoints for a future React dashboard.

## Run (Docker)

```bash
docker build -t den-backend .
docker run --rm -p 8080:8080 -v $PWD/data:/data den-backend
# Ensure /data/live.csv exists and is being appended to.
```

Endpoints:
- `GET /healthz`
- `GET /api/flows/open`
- `GET /api/flows/recent`
- `WS /ws/live`


 uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload