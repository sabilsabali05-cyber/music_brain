from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def new_track_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"trk_{timestamp}_{uuid4().hex[:10]}"
