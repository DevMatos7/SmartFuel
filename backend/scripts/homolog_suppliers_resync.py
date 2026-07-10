"""Homologação SUPPLIERS — re-sync full com coleta de relatório."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
EMAIL = os.environ.get("HOMOLOG_EMAIL", "admin@test.com")
PASSWORD = os.environ.get("HOMOLOG_PASSWORD", "SenhaSegura123")
STATION_ID = os.environ.get("HOMOLOG_STATION_ID", "1edc5c8b-0ba1-405c-a000-03e61e31521e")
POLL_SECONDS = int(os.environ.get("HOMOLOG_POLL_SECONDS", "900"))
POLL_INTERVAL = 5
PREVIOUS_RUN_ID = os.environ.get("PREVIOUS_RUN_ID", "225a483e-18b4-4d30-b64b-6898734ee188")


def login(client: httpx.Client) -> dict[str, str]:
    r = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def wait_run(client: httpx.Client, headers: dict[str, str], run_id: str) -> dict:
    deadline = time.time() + POLL_SECONDS
    run: dict = {}
    while time.time() < deadline:
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            f"  {run['status']} read={run.get('rows_read')} applied={run.get('rows_applied')} "
            f"quarantined={run.get('rows_quarantined')} unchanged={run.get('rows_unchanged')}"
        )
        if run["status"] not in (
            "QUEUED", "CONNECTING", "EXTRACTING", "STAGING", "VALIDATING", "APPLYING", "CANCELLATION_REQUESTED"
        ):
            return run
        time.sleep(POLL_INTERVAL)
    return run


def print_run(label: str, run: dict) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps({
        "id": run.get("id"),
        "status": run.get("status"),
        "sync_mode": run.get("sync_mode"),
        "rows_read": run.get("rows_read"),
        "rows_inserted": run.get("rows_inserted"),
        "rows_updated": run.get("rows_updated"),
        "rows_unchanged": run.get("rows_unchanged"),
        "rows_applied": run.get("rows_applied"),
        "rows_quarantined": run.get("rows_quarantined"),
        "rows_error": run.get("rows_error"),
        "checkpoint_before": run.get("checkpoint_before"),
        "checkpoint_after": run.get("checkpoint_after"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "error_code": run.get("error_code"),
    }, ensure_ascii=False, indent=2, default=str))


def print_diag(client: httpx.Client, headers: dict[str, str], run_id: str, label: str) -> dict | None:
    diag = client.get(
        f"/integrations/xpert/sync-runs/{run_id}/supplier-document-diagnostics", headers=headers
    )
    if diag.status_code == 200:
        body = diag.json()
        print(f"\n=== {label} ===")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return body
    print(f"\n=== {label} === ERRO {diag.status_code}: {diag.text[:200]}")
    return None


def enqueue_suppliers(client: httpx.Client, headers: dict[str, str], source_id: str) -> str:
    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source_id,
            "dataset_codes": ["SUPPLIERS"],
            "station_ids": [STATION_ID],
            "sync_mode": "FULL_SNAPSHOT_HASH",
        },
    )
    if sync.status_code >= 400:
        raise RuntimeError(f"Erro ao enfileirar: {sync.status_code} {sync.text}")
    run_id = sync.json()["runs"][0]["id"]
    print(f"\nRun enfileirada: {run_id}")
    return run_id


def main() -> int:
    unsafe_allowed = os.environ.get("XPERT_ALLOW_UNSAFE_PRIVILEGES", "false").lower() in ("1", "true", "yes")
    sql_user = os.environ.get("XPERT_SQLSERVER_USER", "")
    print("=== PRÉ-CONDIÇÕES ===")
    print(f"XPERT_SQLSERVER_USER={sql_user}")
    print(f"XPERT_ALLOW_UNSAFE_PRIVILEGES={unsafe_allowed}")

    client = httpx.Client(base_url=BASE, timeout=120.0)
    headers = login(client)

    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    if not sources:
        print("Nenhuma fonte XPERT configurada.")
        return 2
    source = sources[0]
    source_id = source["id"]
    print(f"Fonte: {source['code']} ({source_id})")

    test = client.post(f"/integrations/xpert/sources/{source_id}/test-connection", headers=headers)
    test.raise_for_status()
    test_body = test.json()
    print("\n=== TESTE DE CONEXÃO ===")
    print(json.dumps(test_body, ensure_ascii=False, indent=2, default=str))

    if test_body.get("status") not in ("CONNECTED", "UNSAFE"):
        print("Conexão indisponível.")
        return 2

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    suppliers_ds = next(d for d in datasets if d["erp_source_id"] == source_id and d["code"] == "SUPPLIERS")

    checkpoints = client.get(
        "/integrations/xpert/checkpoints",
        headers=headers,
        params={"source_id": source_id, "dataset_id": suppliers_ds["id"], "station_id": STATION_ID},
    ).json()
    print("\n=== CHECKPOINT ANTES ===")
    print(json.dumps(checkpoints, ensure_ascii=False, indent=2, default=str))

    prev = client.get(f"/integrations/xpert/sync-runs/{PREVIOUS_RUN_ID}", headers=headers)
    if prev.status_code == 200:
        print_run("EXECUÇÃO ANTERIOR", prev.json())
        print_diag(client, headers, PREVIOUS_RUN_ID, "DIAGNÓSTICO ANTERIOR (run antiga)")

    run1_id = enqueue_suppliers(client, headers, source_id)
    run1 = wait_run(client, headers, run1_id)
    print_run("NOVA EXECUÇÃO #1", run1)
    diag1 = print_diag(client, headers, run1_id, "DIAGNÓSTICO NOVO #1")

    checkpoints_after = client.get(
        "/integrations/xpert/checkpoints",
        headers=headers,
        params={"source_id": source_id, "dataset_id": suppliers_ds["id"], "station_id": STATION_ID},
    ).json()
    print("\n=== CHECKPOINT DEPOIS ===")
    print(json.dumps(checkpoints_after, ensure_ascii=False, indent=2, default=str))

    print("\n=== IDEMPOTÊNCIA — EXECUÇÃO #2 ===")
    run2_id = enqueue_suppliers(client, headers, source_id)
    run2 = wait_run(client, headers, run2_id)
    print_run("EXECUÇÃO #2 (idempotente)", run2)
    print_diag(client, headers, run2_id, "DIAGNÓSTICO #2")

    print("\n=== RESUMO COMPARATIVO ===")
    prev_run = prev.json() if prev.status_code == 200 else {}
    print(json.dumps({
        "anterior": {
            "run_id": PREVIOUS_RUN_ID,
            "status": prev_run.get("status"),
            "applied": prev_run.get("rows_applied"),
            "quarantined": prev_run.get("rows_quarantined"),
        },
        "nova_1": {
            "run_id": run1_id,
            "status": run1.get("status"),
            "applied": run1.get("rows_applied"),
            "quarantined": run1.get("rows_quarantined"),
            "inserted": run1.get("rows_inserted"),
            "updated": run1.get("rows_updated"),
            "unchanged": run1.get("rows_unchanged"),
        },
        "nova_2": {
            "run_id": run2_id,
            "status": run2.get("status"),
            "inserted": run2.get("rows_inserted"),
            "updated": run2.get("rows_updated"),
            "unchanged": run2.get("rows_unchanged"),
        },
        "diagnostico_novo": diag1,
    }, ensure_ascii=False, indent=2, default=str))

    ok = run1.get("status") == "COMPLETED"
    if ok and run2.get("rows_inserted", 0) == 0:
        return 0
    return 1 if not ok else 0


if __name__ == "__main__":
    sys.exit(main())
