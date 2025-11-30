"""
Structured logger that appends JSON events to logs/run_logs.json
"""

import os
import json
from datetime import datetime

LOGS_PATH_DEFAULT = "logs/run_logs.json"

def log_event(event: str, payload):
    ev = {
        "time": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "payload": payload
    }
    print(json.dumps(ev))
    try:
        os.makedirs(os.path.dirname(LOGS_PATH_DEFAULT), exist_ok=True)
        logs = []
        if os.path.exists(LOGS_PATH_DEFAULT):
            try:
                with open(LOGS_PATH_DEFAULT, "r") as fh:
                    logs = json.load(fh)
            except Exception:
                logs = []
        logs.append(ev)
        with open(LOGS_PATH_DEFAULT, "w") as fh:
            json.dump(logs, fh, indent=2)
    except Exception as e:
        # non-fatal
        print(f"[logger] failed to write logs: {e}")
