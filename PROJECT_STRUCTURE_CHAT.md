# DeepEncryptNet Project Structure Chat (Backend + Frontend Index)

This file is a structured index of the current codebase, focused on:
- `app/` (FastAPI + real-time ML pipeline)
- `frontend/` (React + Vite dashboard)
- What data is already saved in DB and how to expose/use it in the frontend.

## 1) End-to-end architecture (current)

1. Packet metadata CSV batches are produced externally (tracker executable).
2. FastAPI app starts and launches a background flow daemon on lifespan startup.
3. Flow daemon reads batch CSVs, splits them into canonical bidirectional streams, and finalizes streams by timeout/packet count/duration.
4. Finalized streams are converted to statistical flow features and saved to `flow_stats`.
5. Prediction queue triggers async inference (`hybrid_pipeline`) and stores model decisions in `prediction_results`.
6. Dashboard API serves status, analytics, and recent flow summaries.
7. React frontend polls those APIs every 3 seconds and renders overview/analytics/flow tabs.

---

## 2) Backend index (`app/`)

### 2.1 Application entry and lifecycle

- **`app/main.py`**
  - Creates FastAPI app.
  - On startup:
    - calls `ensure_schema()`
    - starts flow daemon thread via `run_flow_daemon(...)`
  - Adds permissive CORS (`*`).
  - Mounts static dashboard assets and SPA fallback routes.

> Important behavior: schema is reset at startup due to `ensure_schema()` implementation.

### 2.2 API layer

- **`app/api/dashboard.py`** (`/api` prefix)
  - `GET /api/status`
  - `GET /api/analytics/classes`
  - `GET /api/analytics/routing`
  - `GET /api/analytics/classified`
  - `GET /api/analytics/routed`
  - `GET /api/analytics/confidence`
  - `GET /api/flows/recent`

These endpoints already provide enough data for a strong operational dashboard.

### 2.3 Flow daemon and stream extraction

- **`app/flow_daemon.py`**
  - Watches `ready_dir` for `*.csv` batches.
  - Moves files ready -> processing -> processed.
  - Runs `PacketStreamDivider`.

- **`app/network_flow_tracker/flow_extractor.py`**
  - Uses canonical 5-tuple flow key (bidirectional normalization).
  - Splits flows when:
    - idle gap threshold exceeded,
    - max packet count reached,
    - max duration reached.
  - Finalizes stream and triggers feature extraction + prediction enqueue.

- **`app/network_flow_tracker/stream_feature_extractor.py`**
  - Reads stream CSV and computes statistics.
  - Persists one `FlowStats` row per flow.

### 2.4 ML inference pipeline

- **`app/pipeline/prediction_queue.py`**
  - ThreadPool-backed async queue.
  - Calls `hybrid_pipeline(flow_id)`.

- **`app/pipeline/caller.py`**
  - Loads features for flow.
  - Runs model inference (`infer_one`).
  - Stores one `PredictionResult` row per flow.

- **`app/pipeline/helpers.py`, `loader.py`, `classifier.py`, `config.py`**
  - Model/config/loading internals.

### 2.5 Persistence and schema

- **`app/database/db.py`**
  - SQLAlchemy engine/session creation from YAML config.

- **`app/database/models/flow_stats.py`**
  - Per-flow timing/rate/IAT statistical feature storage.

- **`app/database/models/prediction_results.py`**
  - Prediction label/action/confidence/margin/entropy/probabilities/embedding.

- **`app/database/init_db.py`**
  - Drops and recreates the entire `public` schema on app startup.

### 2.6 Runtime configuration

- **`app/settings.py`**
  - Loads config from local/docker YAML path.
  - Validates `flow_daemon` and `database` sections.

---

## 3) Database-backed data already available for frontend

### 3.1 `flow_stats` (feature-level telemetry)

Key fields currently persisted and useful for UI:
- Identity/time: `flow_id`, `start_time`, `end_time`, `duration`
- Throughput: `flowBytesPerSecond`, `flowPktsPerSecond`
- Activity: `max_active`, `std_active`
- Inter-arrival features:
  - backward: `max_biat`, `mean_biat`, `min_biat`, `total_biat`
  - forward: `max_fiat`, `mean_fiat`, `min_fiat`, `total_fiat`
  - flow-wide: `max_flowiat`, `mean_flowiat`, `min_flowiat`, `std_flowiat`

### 3.2 `prediction_results` (decision telemetry)

Fields that can directly power UI:
- Decision/label: `predicted_class`, `action`, `pred_idx`
- Uncertainty: `max_p`, `margin`, `entropy`
- Full outputs: `probs`, `embedding`
- Traceability: `model_version`, `manifest_path`, `created_at`

---

## 4) Frontend index (`frontend/`)

### 4.1 App composition

- **`src/App.jsx`** -> renders dashboard page only.
- **`src/pages/Dashboard.tsx`**
  - Tabs: `Overview`, `Analytics`, `Flows`.
  - Polling every 3s.
  - Fetches status, class distribution, routing summary, and recent flows.
  - Shows warning banner if route rate > 25%.

### 4.2 API client

- **`src/api/dashboardApi.ts`** currently uses:
  - `/api/status`
  - `/api/analytics/classes`
  - `/api/analytics/routing`
  - `/api/analytics/confidence` (defined but not used in `Dashboard.tsx`)
  - `/api/flows/recent`

### 4.3 Types

- **`src/types/dashboard.ts`**
  - typed models for status, class distribution, routing summary, confidence/entropy, recent flow row.

### 4.4 Presentational components

- Current visible widgets:
  - Status bar
  - Class distribution list
  - Routing summary block
  - Recent flow table (flow id/class/entropy/threat badge)
- Supporting UI primitives:
  - cards, badges, alert banner, tab bar, animated view.

---

## 5) Feature opportunities for `frontend` based on existing backend + DB

Below are high-value items you can build **without major backend redesign**.

### A) Decision quality + uncertainty panel

Use existing fields (`max_p`, `margin`, `entropy`, `probs`):
- confidence trend (time-series)
- entropy trend
- low-margin alert count
- top-2 class probability gap per recent flow

### B) Routing intelligence panel

Use existing `action` and class data:
- route rate sparkline (1m/5m/15m)
- routed-by-class table
- sudden routing spike detector with thresholds

### C) Flow performance panel

Use `flow_stats` timing/rate fields:
- duration histogram
- bytes/sec and packets/sec percentiles
- top-N heavy flows by estimated bytes

### D) Feature diagnostics panel (for research/demo)

Surface the extracted statistical features:
- per-flow expandable drawer with full feature vector
- z-score/outlier highlight for `flowiat/fiat/biat`

### E) Model observability panel

Use `model_version`, `manifest_path`, `created_at`:
- currently active model version display
- prediction volume per model version
- last inference timestamp + ingest-to-infer lag estimate

### F) Threat operations panel

Leverage existing front-end threat derivation + backend fields:
- threat-severity counts
- critical-only queue
- acknowledge/escalate UI actions (needs small backend endpoint additions)

---

## 6) Suggested near-term frontend backlog

1. **Wire `fetchConfidence()` into Dashboard analytics tab** (already available client-side).
2. Add **time-window selector** (60/300/900 sec) and pass `window_sec` to analytics APIs.
3. Add **recent flow details drawer** with confidence, action, timestamps, throughput metrics.
4. Add **routed-only** and **classified-only** widgets using existing APIs.
5. Add **empty/loading/error states** for each panel.
6. Introduce **single dashboard state store** for cleaner polling + cache control.

---

## 7) Notes / caveats for project planning

- Current startup resets DB schema completely (destructive) — good for experiments, risky for persistent demos.
- `CORS` is currently open (`*`) for all origins.
- API coverage is analytics-focused and good for a monitoring dashboard baseline.

---

## 8) Recommended next step

If you want, next I can create:
1. a **Frontend Feature Matrix** (`endpoint -> data fields -> component -> UX goal`), and
2. a **phased implementation plan** (Phase 1 MVP dashboard polish, Phase 2 observability, Phase 3 operations/actions).
