# app/database/event_listeners.py
from sqlalchemy import event
from app.database.models import FlowStats
import logging

@event.listens_for(FlowStats, "after_insert", propagate=True)
def trigger_prediction(mapper, connection, target: FlowStats):
    """
    SAFE: print-only listener. Do not open/close sessions here.
    Fires during flush — target contains the inserted values.
    """
    try:
        # You can access any column from the new row directly:
        print("prediction triggered", target)              # whole object repr
        print("flow_id:", target.flow_id)                  # primary key
        # print("duration:", target.duration)              # example field
        logging.info(f"[PREDICT-LISTENER] inserted {target.flow_id}")
    except Exception as e:
        logging.warning(f"[PREDICT-LISTENER] print failed for {getattr(target, 'flow_id', '?')}: {e}")




# from sqlalchemy.orm import Session
# from sqlalchemy import event
# import threading
#
# @event.listens_for(Session, "after_commit")
# def on_after_commit(session):
#     new_flows = [obj for obj in session.new if isinstance(obj, FlowStats)]
#     if not new_flows:
#         return
#     # Offload to background thread so we don't block the request cycle
#     def worker(flow_ids):
#         from app.database.db import SessionLocal
#         from app.database.crud import insert_prediction
#         # ... run predict_one, then insert_prediction ...
#         # use a fresh SessionLocal() here safely
#     threading.Thread(target=worker, args=([f.flow_id for f in new_flows],), daemon=True).start()
