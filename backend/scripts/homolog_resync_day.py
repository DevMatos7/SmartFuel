"""Revalida contrato e re-sincroniza um dia."""

from __future__ import annotations

import sys
import time

import httpx

DAY_START = sys.argv[1] if len(sys.argv) > 1 else "2026-07-09"
DAY_END = sys.argv[2] if len(sys.argv) > 2 else "2026-07-10"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"


def main() -> None:
    client = httpx.Client(base_url="http://localhost:8000/api/v1", timeout=180.0)
    token = client.post("/auth/login", json={"email": "admin@test.com", "password": "SenhaSegura123"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    ds = next(d for d in datasets if d["code"] == "FUEL_SALES_ITEMS")
    validate = client.post(
        f"/integrations/xpert/datasets/{ds['id']}/validate-contract",
        headers=headers,
        params={"station_id": STATION},
    )
    print("validate", validate.status_code, validate.json())
    source_id = client.get("/integrations/xpert/sources", headers=headers).json()[0]["id"]
    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source_id,
            "dataset_codes": ["FUEL_SALES_ITEMS"],
            "station_ids": [STATION],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DAY_START,
            "history_end_date": DAY_END,
        },
    )
    sync.raise_for_status()
    run_id = sync.json()["runs"][0]["id"]
    for _ in range(120):
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(run["status"], "read", run.get("rows_read"), "updated", run.get("rows_updated"), "applied", run.get("rows_applied"))
        if run["status"] not in ("QUEUED", "CONNECTING", "EXTRACTING", "STAGING", "VALIDATING", "APPLYING"):
            return
        time.sleep(5)


if __name__ == "__main__":
    main()
