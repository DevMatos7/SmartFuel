"""Sprint 7.1 — validar contratos e homologar um dia de compras (filial 2443)."""

from __future__ import annotations

import sys
import time

import httpx

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-07-09"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
DATASETS = [
    "FUEL_PURCHASE_INVOICES",
    "FUEL_PURCHASE_ITEMS",
    "ACCOUNTS_PAYABLE_TITLES",
]
CONFIRM = "CONFIRMAR HOMOLOGAÇÃO DE COMPRAS XPERT"


def wait_run(client: httpx.Client, headers: dict, run_id: str) -> dict:
    for _ in range(180):
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            run["dataset_code"] if "dataset_code" in run else run.get("status"),
            run["status"],
            "read",
            run.get("rows_read"),
            "applied",
            run.get("rows_applied"),
            "unchanged",
            run.get("rows_unchanged"),
            "err",
            run.get("rows_error"),
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
        time.sleep(3)
    raise TimeoutError(run_id)


def main() -> None:
    client = httpx.Client(base_url="http://localhost:8000/api/v1", timeout=300.0)
    token = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "SenhaSegura123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    by_code = {d["code"]: d for d in datasets}
    source_id = client.get("/integrations/xpert/sources", headers=headers).json()[0]["id"]

    for code in DATASETS:
        ds = by_code[code]
        # habilitar para homologação
        client.patch(
            f"/integrations/xpert/datasets/{ds['id']}",
            headers=headers,
            json={"enabled": True, "schedule_enabled": False},
        )
        validate = client.post(
            f"/integrations/xpert/datasets/{ds['id']}/validate-contract",
            headers=headers,
            params={"station_id": STATION},
        )
        print("validate", code, validate.status_code, validate.json())

    for code in DATASETS:
        sync = client.post(
            "/integrations/xpert/sync-runs",
            headers=headers,
            json={
                "source_id": source_id,
                "dataset_codes": [code],
                "station_ids": [STATION],
                "sync_mode": "INCREMENTAL_TIMESTAMP",
                "unsafe_homologation_acknowledged": True,
                "history_start_date": DAY,
                "history_end_date": DAY,
            },
        )
        print("enqueue", code, sync.status_code, sync.text[:300])
        sync.raise_for_status()
        run_id = sync.json()["runs"][0]["id"]
        wait_run(client, headers, run_id)

    # segunda execução idempotente
    print("=== PASS 2 IDEMPOTENT ===")
    for code in DATASETS:
        sync = client.post(
            "/integrations/xpert/sync-runs",
            headers=headers,
            json={
                "source_id": source_id,
                "dataset_codes": [code],
                "station_ids": [STATION],
                "sync_mode": "INCREMENTAL_TIMESTAMP",
                "unsafe_homologation_acknowledged": True,
                "history_start_date": DAY,
                "history_end_date": DAY,
            },
        )
        sync.raise_for_status()
        wait_run(client, headers, sync.json()["runs"][0]["id"])

    summary = client.get(
        f"/analytics/fuel-purchases/summary?date_from={DAY}&date_to={DAY}",
        headers=headers,
    )
    print("summary", summary.status_code, summary.json())


if __name__ == "__main__":
    main()
