"""Homologação — mapear e reconciliar um produto não mapeado."""

from __future__ import annotations

import json
import sys
from datetime import date

import httpx

BASE = "http://localhost:8000/api/v1"
EMAIL = "admin@test.com"
PASSWORD = "SenhaSegura123"
DATE_FROM = date(2026, 7, 3)
DATE_TO = date(2026, 7, 9)


def login(client: httpx.Client) -> dict[str, str]:
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def summary(client: httpx.Client, headers: dict[str, str]) -> dict:
    return client.get(
        "/analytics/fuel-sales/summary",
        headers=headers,
        params={"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()},
    ).json()


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    headers = login(client)

    before = summary(client, headers)
    unmapped = client.get(
        "/analytics/fuel-sales/unmapped",
        headers=headers,
        params={"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()},
    ).json()
    if not unmapped:
        print(json.dumps({"status": "NO_UNMAPPED_ITEMS", "before": before}, indent=2))
        return 0

    target = unmapped[0]
    erp_product_id = target["erp_product_id"]
    print("target", json.dumps(target, indent=2, ensure_ascii=False))

    products = client.get("/products", headers=headers, params={"page_size": 50}).json()
    canonical_list = products.get("items") or products
    if not canonical_list:
        print(json.dumps({"status": "NO_CANONICAL_PRODUCTS"}, indent=2))
        return 1
    canonical_id = canonical_list[0]["id"]

    map_resp = client.post(
        f"/erp-products/{erp_product_id}/map",
        headers=headers,
        json={"canonical_product_id": canonical_id, "reason": "Homologação Sprint 6 — reconcile test"},
    )
    print("mapping", map_resp.status_code, map_resp.text[:500])
    map_resp.raise_for_status()

    rec = client.post(
        "/analytics/fuel-sales/reconcile-mappings",
        headers=headers,
        json={"erp_product_id": erp_product_id},
    )
    print("reconcile", rec.status_code, rec.text[:500])
    rec.raise_for_status()

    after = summary(client, headers)
    quality = client.get(
        "/analytics/fuel-sales/data-quality",
        headers=headers,
        params={"date_from": DATE_FROM.isoformat(), "date_to": DATE_TO.isoformat()},
    ).json()

    report = {
        "status": "RECONCILED_ONE",
        "erp_product_id": erp_product_id,
        "canonical_product_id": canonical_id,
        "before_summary": before,
        "after_summary": after,
        "summary_unchanged": before == after,
        "data_quality": quality,
        "reconcile_result": rec.json(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["summary_unchanged"] else 2


if __name__ == "__main__":
    sys.exit(main())
