"""Homologação controlada XPERT via API — credenciais somente do ambiente."""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

BASE = os.environ.get("API_BASE_URL", "http://host.docker.internal:8000/api/v1")
STATION_ID = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
EMAIL = "admin@test.com"
PASSWORD = "SenhaSegura123"
POLL_SECONDS = 300
POLL_INTERVAL = 5


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    login = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sources = client.get("/integrations/xpert/sources", headers=headers).json()
    if sources:
        source = sources[0]
        print(f"Fonte existente: {source['id']} ({source['code']})")
        source_id = source["id"]
    else:
        create = client.post(
            "/integrations/xpert/sources",
            headers=headers,
            json={
                "code": "ATX_MATRIZ",
                "name": "ATX Matriz",
                "host": "192.168.120.253",
                "port": 1433,
                "database_name": "atxdados",
                "driver_name": "ODBC Driver 18 for SQL Server",
                "encrypt_connection": True,
                "trust_server_certificate": True,
                "secret_ref": "xpert_atx",
                "source_timezone": "America/Cuiaba",
                "enabled": True,
            },
        )
        if create.status_code >= 400:
            print("Erro ao criar fonte:", create.status_code, create.text)
            return 1
        source = create.json()
        source_id = source["id"]
        print(f"Fonte criada: {source_id}")

    client.patch(
        f"/integrations/xpert/sources/{source_id}",
        headers=headers,
        json={"enabled": True, "trust_server_certificate": True},
    ).raise_for_status()

    test = client.post(f"/integrations/xpert/sources/{source_id}/test-connection", headers=headers)
    test.raise_for_status()
    test_body = test.json()
    print("Teste de conexão:", json.dumps(test_body, ensure_ascii=False, default=str))
    if test_body.get("status") not in ("CONNECTED", "UNSAFE"):
        print("Conexão falhou.")
        return 1

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    by_code = {d["code"]: d for d in datasets if d["erp_source_id"] == source_id}
    for code in ("PRODUCTS", "SUPPLIERS"):
        ds = by_code.get(code)
        if not ds:
            print(f"Dataset {code} não encontrado.")
            return 1
        validate = client.post(
            f"/integrations/xpert/datasets/{ds['id']}/validate-contract",
            headers=headers,
            params={"station_id": STATION_ID},
        )
        if validate.status_code >= 400:
            print(f"Contrato {code} inválido:", validate.status_code, validate.text)
            return 1
        print(f"Contrato {code} validado:", validate.json().get("valid"), "amostra:", validate.json().get("sample_count"))
        client.patch(
            f"/integrations/xpert/datasets/{ds['id']}",
            headers=headers,
            json={"enabled": True},
        ).raise_for_status()

    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source_id,
            "dataset_codes": ["PRODUCTS", "SUPPLIERS"],
            "station_ids": [STATION_ID],
            "sync_mode": "FULL_SNAPSHOT_HASH",
        },
    )
    if sync.status_code >= 400:
        print("Erro ao enfileirar sync:", sync.status_code, sync.text)
        return 1
    runs = sync.json()["runs"]
    run_ids = [r["id"] for r in runs]
    print(f"Runs enfileiradas: {run_ids}")

    deadline = time.time() + POLL_SECONDS
    final: dict[str, dict] = {}
    while time.time() < deadline:
        all_done = True
        for run_id in run_ids:
            run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
            final[run_id] = run
            status = run["status"]
            print(f"  Run {run_id[:8]}… {status} phase={run.get('phase')} "
                  f"extracted={run.get('rows_extracted')} applied={run.get('rows_applied')}")
            if status in ("QUEUED", "CONNECTING", "EXTRACTING", "STAGING", "VALIDATING", "APPLYING"):
                all_done = False
        if all_done:
            break
        time.sleep(POLL_INTERVAL)

    print("\n=== Resultado final ===")
    ok = True
    for run_id, run in final.items():
        print(json.dumps({
            "id": run_id,
            "status": run["status"],
            "rows_extracted": run.get("rows_extracted"),
            "rows_applied": run.get("rows_applied"),
            "rows_inserted": run.get("rows_inserted"),
            "rows_updated": run.get("rows_updated"),
            "rows_quarantined": run.get("rows_quarantined"),
            "error_code": run.get("error_code"),
            "error_message": run.get("error_message"),
        }, ensure_ascii=False))
        if run["status"] != "COMPLETED":
            ok = False

    summary = client.get("/integrations/xpert", headers=headers).json()
    print("Summary:", json.dumps(summary, ensure_ascii=False, default=str))

    counts = client.get(
        "/erp-products",
        headers=headers,
        params={"station_id": STATION_ID, "page": 1, "page_size": 1},
    )
    if counts.status_code == 200:
        print(f"Produtos ERP total: {counts.json().get('total')}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
