"""Sprint 8.2 — cotações de exemplo ativadas (Matriz).

Cria cotações operacionais futuras/presentes com activated_at = agora.
NÃO retroage activated_at para parecer histórico de compras passadas.

Uso (host com API em :8000):
  python scripts/homolog_sprint82_seed_quotes.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

BASE = "http://localhost:8000/api/v1"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
EMAIL = "admin@test.com"
PASSWORD = "SenhaSegura123"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"

# Preços ilustrativos por família (R$/L) — exemplos operacionais
QUOTE_SPECS = [
    {"product_code": "ETANOL_HIDRATADO", "price": "3.8900", "min_vol": "5000.000", "dist_code": "DIST-EX-A"},
    {"product_code": "GASOLINA_C_COMUM", "price": "5.7900", "min_vol": "5000.000", "dist_code": "DIST-EX-A"},
    {"product_code": "DIESEL_B_S10_COMUM", "price": "5.4500", "min_vol": "10000.000", "dist_code": "DIST-EX-A"},
    {"product_code": "ETANOL_HIDRATADO", "price": "3.9200", "min_vol": "5000.000", "dist_code": "DIST-EX-B"},
    {"product_code": "GASOLINA_C_COMUM", "price": "5.8100", "min_vol": "5000.000", "dist_code": "DIST-EX-B"},
    {"product_code": "DIESEL_B_S10_COMUM", "price": "5.4800", "min_vol": "10000.000", "dist_code": "DIST-EX-B"},
]


def _out_dir() -> Path:
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        docs = root / "docs" / "sprints"
        if (root / "docs").is_dir():
            docs.mkdir(parents=True, exist_ok=True)
            return docs
    p = Path("/tmp/sprint-docs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_distributor(client: httpx.Client, headers: dict, code: str, cnpj: str) -> dict:
    listing = client.get("/distributors", headers=headers, params={"search": code})
    listing.raise_for_status()
    for item in listing.json().get("items", []):
        if item.get("internal_code") == code:
            return item
    created = client.post(
        "/distributors",
        headers=headers,
        json={
            "internal_code": code,
            "corporate_name": f"{code} LTDA",
            "trade_name": code,
            "cnpj": cnpj,
            "active": True,
        },
    )
    if created.status_code not in (200, 201):
        # tenta listar de novo
        listing = client.get("/distributors", headers=headers)
        listing.raise_for_status()
        for item in listing.json().get("items", []):
            if item.get("internal_code") == code:
                return item
        print("distributor create failed", created.status_code, created.text, file=sys.stderr)
        created.raise_for_status()
    return created.json()


def ensure_supplier_rule(
    client: httpx.Client,
    headers: dict,
    *,
    station_id: str,
    distributor_id: str,
    product_id: str,
) -> None:
    valid_from = datetime.now(UTC).date().isoformat()
    resp = client.post(
        "/station-supplier-rules",
        headers=headers,
        json={
            "station_id": station_id,
            "distributor_id": distributor_id,
            "product_id": product_id,
            "allowed": True,
            "minimum_volume_liters": "1000.000",
            "valid_from": valid_from,
            "priority": 100,
            "reason": "Sprint 8.2 — cotações de exemplo",
        },
    )
    # 201 ok; 409/400 se já existir — seguir
    if resp.status_code not in (200, 201, 409, 400, 422):
        print("rule warn", resp.status_code, resp.text[:200])


def create_active_quote(
    client: httpx.Client,
    headers: dict,
    *,
    station_id: str,
    distributor_id: str,
    product_id: str,
    payment_term_id: str,
    price: str,
    minimum_volume: str,
) -> dict:
    now = datetime.now(UTC)
    q = client.post(
        "/quotes",
        headers=headers,
        json={
            "station_id": station_id,
            "distributor_id": distributor_id,
            "quoted_at": now.isoformat(),
            "valid_until": (now + timedelta(days=7)).isoformat(),
            "source_channel": "EMAIL",
            "entry_method": "MANUAL",
            "seller_name": "Homolog Sprint 8.2",
            "seller_contact": "homolog@example.com",
            "notes": "Cotação de exemplo operacional — activated_at = agora (não retroativa)",
            "origin": "SYNTHETIC_TEST",
            "analytics_eligible": False,
        },
    )
    q.raise_for_status()
    quote = q.json()
    item = client.post(
        f"/quotes/{quote['id']}/items",
        headers=headers,
        json={
            "expected_version": quote["version"],
            "product_id": product_id,
            "payment_term_id": payment_term_id,
            "quoted_price_per_liter": price,
            "minimum_volume_liters": minimum_volume,
            "freight_type": "CIF",
            "freight_calculation_type": "NONE",
        },
    )
    item.raise_for_status()
    quote = client.get(f"/quotes/{quote['id']}", headers=headers).json()
    ev = client.post(
        f"/quotes/{quote['id']}/evidences",
        headers=headers,
        data={"expected_version": str(quote["version"]), "category": "PDF_PROPOSAL"},
        files={"file": ("exemplo-sprint82.pdf", PDF_BYTES, "application/pdf")},
    )
    ev.raise_for_status()
    quote = ev.json()
    act = client.post(
        f"/quotes/{quote['id']}/activate",
        headers=headers,
        json={"expected_version": quote["version"]},
    )
    act.raise_for_status()
    return act.json()


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}

    products = client.get("/products", headers=headers).json()["items"]
    by_code = {p["code"]: p for p in products}
    terms = client.get("/payment-terms", headers=headers).json()["items"]
    cash = next(t for t in terms if t.get("days") == 0)

    dist_a = ensure_distributor(client, headers, "DIST-EX-A", "11222333000858")
    dist_b = ensure_distributor(client, headers, "DIST-EX-B", "11222333000424")
    dists = {"DIST-EX-A": dist_a, "DIST-EX-B": dist_b}

    created = []
    for spec in QUOTE_SPECS:
        product = by_code.get(spec["product_code"])
        if product is None:
            print("skip missing product", spec["product_code"])
            continue
        dist = dists[spec["dist_code"]]
        ensure_supplier_rule(
            client,
            headers,
            station_id=STATION,
            distributor_id=dist["id"],
            product_id=product["id"],
        )
        quote = create_active_quote(
            client,
            headers,
            station_id=STATION,
            distributor_id=dist["id"],
            product_id=product["id"],
            payment_term_id=cash["id"],
            price=spec["price"],
            minimum_volume=spec["min_vol"],
        )
        created.append(
            {
                "quote_id": quote["id"],
                "quote_number": quote.get("quote_number"),
                "product_code": spec["product_code"],
                "distributor": spec["dist_code"],
                "price": spec["price"],
                "activated_at": quote.get("activated_at"),
                "valid_until": quote.get("valid_until"),
                "status": quote.get("status"),
            }
        )
        print("activated", quote.get("quote_number"), spec["product_code"], spec["price"])

    out = _out_dir() / "sprint-08-2-example-quotes.json"
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "station_id": STATION,
        "note": (
            "Cotações de exemplo com activated_at = momento da criação. "
            "Não são evidência histórica de compras anteriores a T."
        ),
        "quotes": created,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out, "count", len(created))


if __name__ == "__main__":
    main()
