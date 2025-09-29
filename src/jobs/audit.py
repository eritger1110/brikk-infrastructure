# src/jobs/audit.py
from datetime import datetime, timezone
def record_audit(event_type: str, payload: dict):
    # Keep simple now; swap to DB table later
    print(f"[AUDIT] {datetime.now(timezone.utc).isoformat()} {event_type} {payload}")
