from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool):
        return value
    if isinstance(value, (datetime, date)):
        if isinstance(value, datetime):
            return value.isoformat()
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _normalize_value(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, (int, float, str)):
        return str(value).strip()
    return str(value)


def canonical_record_hash(payload: dict[str, Any]) -> str:
    normalized = _normalize_value(payload)
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def query_file_hash(sql: str) -> str:
    return hashlib.sha256(sql.strip().encode("utf-8")).hexdigest()
