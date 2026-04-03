"""
Agent Logger — LangSmith-style audit logging
--------------------------------------------
Stores all agent actions in memory and writes to logs/audit.jsonl
Each log entry is a JSON object on its own line (JSONL format).
"""

import os
import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "audit.jsonl"


class AgentLogger:
    def __init__(self):
        LOG_DIR.mkdir(exist_ok=True)
        self._entries = []

    def _write(self, level: str, run_id: str, message: str):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "run_id": run_id,
            "message": message,
        }
        self._entries.append(entry)
        # Append to JSONL file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        # Also print to console
        icon = {"INFO": "ℹ", "SUCCESS": "✓", "WARNING": "⚠", "ERROR": "✗"}.get(level, "·")
        print(f"[{entry['ts']}] {icon} [{level}] [{run_id}] {message}")

    def info(self, run_id: str, message: str):
        self._write("INFO", run_id, message)

    def success(self, run_id: str, message: str):
        self._write("SUCCESS", run_id, message)

    def warning(self, run_id: str, message: str):
        self._write("WARNING", run_id, message)

    def error(self, run_id: str, message: str):
        self._write("ERROR", run_id, message)

    def get_all(self) -> list:
        return self._entries

    def get_by_run(self, run_id: str) -> list:
        return [e for e in self._entries if e["run_id"] == run_id]
