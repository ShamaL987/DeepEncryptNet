from fastapi import FastAPI
import threading
from app.flow_daemon import tail_loop, CONFIG

app = FastAPI(title="DeepEncryptNet Flow Daemon")

_runner_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None

@app.on_event("startup")
def start_daemon():
    global _runner_thread, _stop_event
    if _runner_thread and _runner_thread.is_alive():
        return
    _stop_event = threading.Event()
    _runner_thread = threading.Thread(target=tail_loop, args=(CONFIG, _stop_event), daemon=True)
    print("[FastAPI] Starting background flow daemon...")
    _runner_thread.start()

@app.on_event("shutdown")
def stop_daemon():
    global _runner_thread, _stop_event
    if _stop_event:
        print("[FastAPI] Stopping background flow daemon...")
        _stop_event.set()
    if _runner_thread:
        _runner_thread.join(timeout=10)

@app.get("/status")
def status():
    alive = bool(_runner_thread and _runner_thread.is_alive())
    return {"daemon_running": alive, "csv_path": CONFIG["csv_path"], "output_dir": CONFIG["output_dir"]}

@app.get("/")
def root():
    return {"message": "Flow daemon running. Check /status"}
