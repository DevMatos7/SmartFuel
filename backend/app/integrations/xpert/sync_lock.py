from __future__ import annotations

import hashlib
import uuid


def sync_lock_key(*, source_id: uuid.UUID, dataset_id: uuid.UUID, station_id: uuid.UUID | None) -> int:
    raw = f"{source_id}:{dataset_id}:{station_id or 'none'}"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
