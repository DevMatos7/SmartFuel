"""Homologação Sprint 6 — PAYMENT_METHODS, FUEL_RETAIL_PRICES, FUEL_SALES_ITEMS."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("HOMOLOG_EMAIL", "admin@test.com")
PASSWORD = os.environ.get("HOMOLOG_PASSWORD", "SenhaSegura123")
STATION_ID = os.environ.get("HOMOLOG_STATION_ID", "1edc5c8b-0ba1-405c-a000-03e61e31521e")
POLL_SECONDS = int(os.environ.get("HOMOLOG_POLL_SECONDS", "900"))
POLL_INTERVAL = 5
HISTORY_DAYS = int(os.environ.get("HOMOLOG_HISTORY_DAYS", "30"))

FUEL_DATASETS = ("PAYMENT_METHODS", "FUEL_RETAIL_PRICES", "FUEL_SALES_ITEMS")


def login(client: httpx.Client) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str) -> dict:
    deadline = time.time() + POLL_SECONDS
    run: dict = {}
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            f"  {run['status']} read={run.get('rows_read')} extracted={run.get('rows_extracted')} "
            f"applied={run.get('rows_applied')} error={run.get('rows_error')}"
        )
        if run["status"] not in (
            "QUEUED",
            "CONNECTING",
            "EXTRACTING",
            "STAGING",
            "VALIDATING",
            "APPLYING",
            "CANCELLATION_REQUESTED",
        ):
            return run
        time.sleep(POLL_INTERVAL)
    return run


def print_run(label: str, run: dict) -> None:
    print(f"\n=== {label} ===")
    print(
        json.dumps(
            {
                "id": run.get("id"),
                "status": run.get("status"),
                "dataset_code": run.get("dataset_code"),
                "sync_mode": run.get("sync_mode"),
                "rows_read": run.get("rows_read"),
                "rows_extracted": run.get("rows_extracted"),
                "rows_inserted": run.get("rows_inserted"),
                "rows_updated": run.get("rows_updated"),
                "rows_applied": run.get("rows_applied"),
                "rows_error": run.get("rows_error"),
                "window_start": run.get("window_start"),
                "window_end": run.get("window_end"),
                "error_code": run.get("error_code"),
                "error_message": run.get("error_message"),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def validate_dataset(
    client: httpx.Client,
    headers: dict[str, str],
    dataset_id: str,
    code: str,
) -> bool:
    response = client.post(
        f"/integrations/xpert/datasets/{dataset_id}/validate-contract",
        headers=headers,
        params={"station_id": STATION_ID},
    )
    if response.status_code >= 400:
        print(f"Contrato {code} inválido: {response.status_code} {response.text}")
        return False
    body = response.json()
    print(
        f"Contrato {code}: valid={body.get('valid')} sample={body.get('sample_count')} "
        f"columns={len(body.get('columns') or [])}"
    )
    if not body.get("valid"):
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return False
    client.patch(
        f"/integrations/xpert/datasets/{dataset_id}",
        headers=headers,
        json={"enabled": True},
    ).raise_for_status()
    return True


def enqueue_sync(
    client: httpx.Client,
    headers: dict[str, str],
    source_id: str,
    dataset_code: str,
    *,
    sync_mode: str,
    history_start: date | None = None,
    history_end: date | None = None,
) -> str:
    payload: dict = {
        "source_id": source_id,
        "dataset_codes": [dataset_code],
        "station_ids": [STATION_ID],
        "sync_mode": sync_mode,
        "unsafe_homologation_acknowledged": True,
    }
    if history_start and history_end:
        payload["history_start_date"] = history_start.isoformat()
        payload["history_end_date"] = history_end.isoformat()

    response = client.post("/integrations/xpert/sync-runs", headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Erro ao enfileirar {dataset_code}: {response.status_code} {response.text}")
    run_id = response.json()["runs"][0]["id"]
    print(f"\nRun {dataset_code} enfileirada: {run_id}")
    return run_id


def main() -> int:
    print("=== PRÉ-CONDIÇÕES ===")
    print(f"API_BASE_URL={BASE}")
    print(f"STATION_ID={STATION_ID}")
    print(f"HISTORY_DAYS={HISTORY_DAYS}")
    print(f"XPERT_ALLOW_UNSAFE_PRIVILEGES={os.environ.get('XPERT_ALLOW_UNSAFE_PRIVILEGES', '')}")

    client = httpx.Client(base_url=BASE, timeout=180.0)
    headers = login(client)

    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    if not sources:
        print("Nenhuma fonte XPERT configurada.")
        return 2
    source = sources[0] if isinstance(sources, list) else sources
    source_id = source["id"]
    print(f"Fonte: {source['code']} security={source.get('security_status')} ({source_id})")

    test = client.post(f"/integrations/xpert/sources/{source_id}/test-connection", headers=headers)
    test.raise_for_status()
    test_body = test.json()
    print("\n=== TESTE DE CONEXÃO ===")
    print(json.dumps(test_body, ensure_ascii=False, indent=2, default=str))
    if test_body.get("status") not in ("CONNECTED", "UNSAFE"):
        return 1

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    by_code = {d["code"]: d for d in datasets if d["erp_source_id"] == source_id}
    for code in FUEL_DATASETS:
        dataset = by_code.get(code)
        if dataset is None:
            print(f"Dataset {code} não encontrado.")
            return 1
        if not validate_dataset(client, headers, dataset["id"], code):
            return 1

    history_end = date.today()
    history_start = history_end - timedelta(days=HISTORY_DAYS)

    runs: list[tuple[str, dict]] = []
    for dataset_code, sync_mode in (
        ("PAYMENT_METHODS", "FULL_SNAPSHOT_HASH"),
        ("FUEL_RETAIL_PRICES", "FULL_SNAPSHOT_HASH"),
        ("FUEL_SALES_ITEMS", "INCREMENTAL_TIMESTAMP"),
    ):
        run_id = enqueue_sync(
            client,
            headers,
            source_id,
            dataset_code,
            sync_mode=sync_mode,
            history_start=history_start if dataset_code == "FUEL_SALES_ITEMS" else None,
            history_end=history_end if dataset_code == "FUEL_SALES_ITEMS" else None,
        )
        run = wait_run(client, headers, run_id)
        print_run(dataset_code, run)
        runs.append((dataset_code, run))
        if run["status"] not in ("COMPLETED", "PARTIAL"):
            return 1
        if run["status"] == "PARTIAL" and int(run.get("rows_error") or 0) > 10:
            print(f"Abortando: muitos erros em {dataset_code}.")
            return 1

    date_to = history_end.isoformat()
    date_from = history_start.isoformat()
    analytics_params = {"date_from": date_from, "date_to": date_to}

    summary = client.get("/analytics/fuel-sales/summary", headers=headers, params=analytics_params)
    quality = client.get("/analytics/fuel-sales/data-quality", headers=headers, params=analytics_params)
    freshness = client.get("/analytics/fuel-sales/freshness", headers=headers)

    print("\n=== ANALYTICS ===")
    if summary.status_code == 200:
        print("Summary:", json.dumps(summary.json(), ensure_ascii=False, indent=2))
    else:
        print("Summary erro:", summary.status_code, summary.text[:300])
    if quality.status_code == 200:
        print("Qualidade:", json.dumps(quality.json(), ensure_ascii=False, indent=2))
    if freshness.status_code == 200:
        print("Freshness:", json.dumps(freshness.json(), ensure_ascii=False, indent=2))

    print("\n=== HOMOLOGAÇÃO CONCLUÍDA ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
