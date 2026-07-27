from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JobLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, level: str, message: str, **fields: Any) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            **fields,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")

    def info(self, message: str, **fields: Any) -> None:
        self.write("info", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.write("warning", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.write("error", message, **fields)

