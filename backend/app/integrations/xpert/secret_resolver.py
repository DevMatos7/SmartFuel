from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.integrations.xpert.canonical_hash import query_file_hash
from app.integrations.xpert.query_validator import validate_parameters, validate_read_only_query

QUERIES_DIR = Path(__file__).resolve().parent / "queries"


def load_query_file(relative_path: str) -> str:
    path = QUERIES_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Query file not found: {relative_path}")
    return path.read_text(encoding="utf-8")


def validate_query_file(relative_path: str) -> dict[str, Any]:
    sql = load_query_file(relative_path)
    validation = validate_read_only_query(sql)
    param_errors = validate_parameters(sql)
    return {
        "query_file": relative_path,
        "query_hash": query_file_hash(sql),
        "valid": validation.valid and not param_errors,
        "errors": validation.errors + param_errors,
    }


def resolve_secret(secret_ref: str) -> dict[str, str]:
    """Resolve credentials from env/file/docker secret — never persisted in DB."""
    env_user = os.environ.get(f"{secret_ref.upper()}_USER") or os.environ.get("XPERT_SQLSERVER_USER", "")
    env_password = os.environ.get(f"{secret_ref.upper()}_PASSWORD") or os.environ.get(
        "XPERT_SQLSERVER_PASSWORD", ""
    )
    file_path = os.environ.get(f"{secret_ref.upper()}_SECRET_FILE") or os.environ.get(
        f"XPERT_SECRET_FILE_{secret_ref.upper()}"
    )
    if file_path and Path(file_path).exists():
        content = Path(file_path).read_text(encoding="utf-8").strip()
        if ":" in content:
            user, password = content.split(":", 1)
            return {"user": user.strip(), "password": password.strip()}
        return {"user": env_user, "password": content}
    if not env_user or not env_password:
        raise ValueError(f"Secret not found for ref: {secret_ref}")
    return {"user": env_user, "password": env_password}
