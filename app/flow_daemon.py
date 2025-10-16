def tail_loop(cfg: dict, stop_event=None):
    """
    Run the CSV tailer until stop_event is set.
    """
    import csv, os, sqlite3, time
    from pathlib import Path
    from app.flow_tracker import StateDB, FlowTracker  # your existing classes

    csv_path = Path(cfg["csv_path"]).resolve()
    out_dir = Path(cfg["output_dir"]); out_dir.mkdir(parents=True, exist_ok=True)

    db = StateDB(Path(cfg["db_path"]))
    tracker = FlowTracker(cfg, db)

    cp_path, cp_inode, cp_mtime, cp_off = db.load_checkpoint()
    last_off = cp_off if cp_path == str(csv_path) else 0

    poll = float(cfg.get("poll_interval_sec", 2.0))
    header_cache = None

    while not (stop_event and stop_event.is_set()):
        try:
            if not csv_path.exists():
                _sleep(stop_event, poll)
                continue

            stat = csv_path.stat()
            inode = f"{stat.st_dev}-{getattr(stat, 'st_ino', 0)}"
            mtime = stat.st_mtime

            if (cp_path != str(csv_path)) or (cp_inode and cp_inode != inode) or (stat.st_size < last_off):
                last_off = 0
                header_cache = None

            with csv_path.open("r", newline="") as f:
                f.seek(0)
                reader = csv.reader(f)
                header = next(reader, None)
                if header_cache is None and header:
                    header_cache = header

                f.seek(last_off)
                # Use DictReader with fixed header when offset > 0
                if last_off > 0 and header_cache:
                    dict_reader = csv.DictReader(f, fieldnames=header_cache)
                else:
                    dict_reader = csv.DictReader(f)

                for row in dict_reader:
                    tracker.add_packet(row)

                last_off = f.tell()

            db.save_checkpoint(str(csv_path), inode, mtime, last_off)
            tracker.flush_timeouts(time.time())

        except Exception as e:
            print(f"[flow-daemon] Error: {e}")

        _sleep(stop_event, poll)

def _sleep(stop_event, seconds: float):
    if not stop_event:
        time.sleep(seconds)
        return
    # sleep in small chunks so shutdown is responsive
    remaining = seconds
    step = 0.1
    while remaining > 0 and not stop_event.is_set():
        time.sleep(min(step, remaining))
        remaining -= step
