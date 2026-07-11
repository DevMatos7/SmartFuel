"""Revalida PRODUCTS (inclui inativos), sincroniza e reexecuta vendas 30 dias."""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta

import httpx

BASE = "http://localhost:8000/api/v1"
EMAIL = "admin@test.com"
PASSWORD = "SenhaSegura123"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
DATE_FROM = date(2026, 6, 10)
DATE_TO = date(2026, 7, 9)


def login(client: httpx.Client) -> dict[str, str]:
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str, label: str) -> dict:
    deadline = time.time() + 3600
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            f"[{label}] {run['status']} read={run.get('rows_read')} "
            f"ins={run.get('rows_inserted')} upd={run.get('rows_updated')} "
            f"unch={run.get('rows_unchanged')} err={run.get('rows_error')}",
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
    raise TimeoutError(label)


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180.0)
    headers = login(client)
    source = client.get("/integrations/xpert/sources", headers=headers).json()[0]
    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    products_ds = next(d for d in datasets if d["code"] == "PRODUCTS")
    sales_ds = next(d for d in datasets if d["code"] == "FUEL_SALES_ITEMS")

    validate = client.post(
        f"/integrations/xpert/datasets/{products_ds['id']}/validate-contract",
        headers=headers,
        params={"station_id": STATION},
    )
    print("validate_products", validate.status_code, validate.json())
    validate.raise_for_status()

    # Sync PRODUCTS (includes inactive 1136)
    sync_p = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source["id"],
            "dataset_codes": ["PRODUCTS"],
            "station_ids": [STATION],
            "sync_mode": "FULL",
            "unsafe_homologation_acknowledged": True,
        },
    )
    sync_p.raise_for_status()
    products_run = wait_run(client, headers, sync_p.json()["runs"][0]["id"], "PRODUCTS")

    # Sales 30d pass 1
    sync_s = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source["id"],
            "dataset_codes": ["FUEL_SALES_ITEMS"],
            "station_ids": [STATION],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DATE_FROM.isoformat(),
            "history_end_date": DATE_TO.isoformat(),
        },
    )
    sync_s.raise_for_status()
    sales_run1 = wait_run(client, headers, sync_s.json()["runs"][0]["id"], "SALES_PASS1")

    # Sales 30d pass 2 idempotency
    sync_s2 = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source["id"],
            "dataset_codes": ["FUEL_SALES_ITEMS"],
            "station_ids": [STATION],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DATE_FROM.isoformat(),
            "history_end_date": DATE_TO.isoformat(),
        },
    )
    sync_s2.raise_for_status()
    sales_run2 = wait_run(client, headers, sync_s2.json()["runs"][0]["id"], "SALES_PASS2")

    params = {"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()}
    summary = client.get("/analytics/fuel-sales/summary", headers=headers, params=params).json()
    quality = client.get("/analytics/fuel-sales/data-quality", headers=headers, params=params).json()

    payload = {
        "products_query_hash": client.get("/integrations/xpert/datasets", headers=headers).json(),
        "products_run": products_run,
        "sales_pass1": sales_run1,
        "sales_pass2": sales_run2,
        "summary": summary,
        "data_quality": quality,
        "sales_dataset_hash": sales_ds.get("query_hash"),
    }
    # simplify products hash
    refreshed = next(d for d in payload["products_query_hash"] if d["code"] == "PRODUCTS")
    payload["products_query_hash"] = refreshed.get("query_hash")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    with open("docs/sprints/sprint-06-etapa-c-completed.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    ok = (
        sales_run1.get("status") == "COMPLETED"
        and sales_run2.get("status") == "COMPLETED"
        and sales_run1.get("rows_error", 1) == 0
        and sales_run2.get("rows_error", 1) == 0
        and sales_run1.get("checkpoint_before") == sales_run1.get("checkpoint_after")
        and sales_run2.get("checkpoint_before") == sales_run2.get("checkpoint_after")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
