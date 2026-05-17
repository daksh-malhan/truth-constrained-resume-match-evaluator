from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .. import database


def log_event(
    run_id: str,
    event_type: str,
    message: str,
    *,
    level: str = "info",
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
) -> None:
    database.insert_log(
        {
            "id": f"log_{uuid.uuid4().hex}",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "message": message,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
            "level": level,
        }
    )

