"""Etapa C — homologação controlada 30 dias (10/06/2026 a 09/07/2026)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("HOMOLOG_EMAIL", "admin@test.com")
PASSWORD = os.environ.get("HOMOLOG_PASSWORD", "SenhaSegura123")
STATION_ID = os.environ.get("HOMOLOG_STATION_ID", "1edc5c8b-0ba1-405c-a000-03e61e31521e")
DATE_FROM = date.fromisoformat(os.environ.get("HOMOLOG_DATE_FROM", "2026-06-10"))
DATE_TO = date.fromisoformat(os.environ.get("HOMOLOG_DATE_TO", "2026-07-09"))
POLL_SECONDS = int(os.environ.get("HOMOLOG_POLL_SECONDS", "3600"))
PASS = int(sys.argv[1]) if len(sys.argv) > 1 else 1
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"docs/sprints/sprint-06-etapa-c-run-pass{PASS}.json")


def login(client: httpx.Client) -> dict[str, str]:
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str) -> dict:
    deadline = time.time() + POLL_SECONDS
    run: dict = {}
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            f"  {run['status']} read={run.get('rows_read')} applied={run.get('rows_applied')} "
            f"ins={run.get('rows_inserted')} upd={run.get('rows_updated')} "
            f"unch={run.get('rows_unchanged')} err={run.get('rows_error')} q={run.get('rows_quarantined')}",
            flush=True,
        )
        if run["status"] not in (
            "QUEUED",
            "CONNECTING",
            "EXTRACTING",
            "STAGING",
            "VALIDATING",
            "APPLYING",
        ):
            return run
        time.sleep(5)
    return run


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180.0)
    headers = login(client)
    me = client.get("/auth/me", headers=headers).json()
    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    source = sources[0]
    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    ds = next(d for d in datasets if d["code"] == "FUEL_SALES_ITEMS")

    history_end = DATE_TO  # enqueue soma +1 dia → window_end exclusivo
    started = time.time()
    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source["id"],
            "dataset_codes": ["FUEL_SALES_ITEMS"],
            "station_ids": [STATION_ID],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DATE_FROM.isoformat(),
            "history_end_date": history_end.isoformat(),
        },
    )
    sync.raise_for_status()
    run_id = sync.json()["runs"][0]["id"]
    print(f"pass={PASS} run_id={run_id}", flush=True)
    run = wait_run(client, headers, run_id)
    elapsed = int(time.time() - started)

    params = {"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()}
    summary = client.get("/analytics/fuel-sales/summary", headers=headers, params=params).json()
    quality = client.get("/analytics/fuel-sales/data-quality", headers=headers, params=params).json()

    payload = {
        "pass": PASS,
        "admin": me.get("email"),
        "period": {"from": DATE_FROM.isoformat(), "to": DATE_TO.isoformat()},
        "station_id": STATION_ID,
        "source_security_status": source.get("security_status"),
        "dataset_query_hash": ds.get("query_hash"),
        "run": run,
        "elapsed_seconds": elapsed,
        "summary": summary,
        "data_quality": quality,
        "checkpoint_before": run.get("checkpoint_before"),
        "checkpoint_after": run.get("checkpoint_after"),
        "normalization_version": run.get("normalization_version"),
        "hash_schema_version": run.get("hash_schema_version"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print(f"Salvo: {OUT}", flush=True)
    return 0 if run.get("status") in ("COMPLETED", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
