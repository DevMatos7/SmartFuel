"""Sprint 7.1 — re-sync metadados NF-e (COMPENTRADAS) só FUEL_PURCHASE_INVOICES."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.query_contracts import validate_contract
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpSource

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-07-09"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
DATASET = "FUEL_PURCHASE_INVOICES"
BRANCH = 2443
OUT = f"/tmp/sprint-07-1-resync-invoices-meta-{DAY}.json"


def wait_run(client: httpx.Client, headers: dict, run_id: str) -> dict:
    for _ in range(180):
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            "run",
            run.get("status"),
            "read",
            run.get("rows_read"),
            "ins",
            run.get("rows_inserted"),
            "upd",
            run.get("rows_updated"),
            "unch",
            run.get("rows_unchanged"),
            "err",
            run.get("rows_error"),
            "ck_before",
            run.get("checkpoint_before"),
            "ck_after",
            run.get("checkpoint_after"),
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


async def probe_xpert() -> dict:
    async with AsyncSessionLocal() as db:
        source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    cur = ds._connect().cursor()  # noqa: SLF001

    cur.execute(
        f"""
        SELECT C.ID_COMPROVANTE, C.NROCOMPROVANTE, C.SAIDAS_ENTRADAS, C.VLRTOTAL, C.SERIE,
               (
                 SELECT COUNT(*)
                 FROM COMPENTRADAS CE
                 WHERE CE.ID_COMPROVANTE = C.ID_COMPROVANTE
                   AND CE.ID_FILIAL = C.ID_FILIAL
                   AND CE.ID_DB = C.ID_DB
               ) AS ce_cnt
        FROM COMPROVANTES C
        WHERE C.ID_FILIAL = {BRANCH}
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
          AND C.DTACONTA >= '{DAY}'
          AND C.DTACONTA < DATEADD(day, 1, CAST('{DAY}' AS date))
        ORDER BY C.ID_COMPROVANTE
        """
    )
    raw = cur.fetchall()
    print("=== RAW COMPROVANTES ===")
    for r in raw:
        print(r)

    cur.execute(
        f"""
        SELECT CE.ID_COMPROVANTE, COUNT(*) AS cnt
        FROM COMPENTRADAS CE
        INNER JOIN COMPROVANTES C
          ON C.ID_COMPROVANTE = CE.ID_COMPROVANTE
         AND C.ID_FILIAL = CE.ID_FILIAL
         AND C.ID_DB = CE.ID_DB
        WHERE CE.ID_FILIAL = {BRANCH}
          AND C.DTACONTA >= '{DAY}'
          AND C.DTACONTA < DATEADD(day, 1, CAST('{DAY}' AS date))
          AND C.SAIDAS_ENTRADAS IN (1, 9, 21)
        GROUP BY CE.ID_COMPROVANTE
        HAVING COUNT(*) > 1
        """
    )
    multi = cur.fetchall()
    print("=== multi COMPENTRADAS ===", multi)

    sql = load_query_file("fuel_purchase_invoices.sql")
    query_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    day_dt = date.fromisoformat(DAY)
    params = {
        "station_erp_id": BRANCH,
        "window_start": datetime(day_dt.year, day_dt.month, day_dt.day, tzinfo=UTC),
        "window_end": datetime(day_dt.year, day_dt.month, day_dt.day, tzinfo=UTC) + timedelta(days=1),
    }
    probe = ds.probe_contract(sql, params, limit=50)
    rows = probe.sample_rows
    # Also stream all via same params as sync
    all_rows: list[dict] = []
    for batch in ds.stream_rows(sql, params, batch_size=100):
        all_rows.extend(batch)
    rows = all_rows
    ids = [str(r["source_invoice_id"]) for r in rows]
    keys = [r.get("source_access_key") for r in rows]
    xml_flags = [bool(r.get("source_xml_imported_in_erp")) for r in rows]
    bad_keys = [k for k in keys if k and (len(str(k)) != 44 or not str(k).isdigit())]
    dup_ids = {k: v for k, v in Counter(ids).items() if v > 1}
    dup_keys = {k: v for k, v in Counter([k for k in keys if k]).items() if v > 1}
    branches = {str(r.get("source_branch_id")) for r in rows}
    contract = validate_contract(DATASET, probe.columns)

    freight = sum((Decimal(str(r.get("source_freight_amount") or 0)) for r in rows), Decimal("0"))
    insurance = sum((Decimal(str(r.get("source_insurance_amount") or 0)) for r in rows), Decimal("0"))
    other = sum((Decimal(str(r.get("source_other_expenses") or 0)) for r in rows), Decimal("0"))

    out = {
        "query_hash": query_hash,
        "raw_comprovantes": len(raw),
        "query_rows": len(rows),
        "unique_invoice_ids": len(set(ids)),
        "with_key": sum(1 for k in keys if k),
        "without_key": sum(1 for k in keys if not k),
        "imported_xml_flag": sum(1 for f in xml_flags if f),
        "bad_keys": bad_keys,
        "dup_invoice_ids": dup_ids,
        "dup_keys": dup_keys,
        "branches": sorted(branches),
        "multi_compentradas": [list(x) for x in multi],
        "contract_valid": contract.valid,
        "contract_missing": contract.missing_columns,
        "contract_extra": contract.extra_columns,
        "probe_columns": probe.columns,
        "freight_total": str(freight),
        "insurance_total": str(insurance),
        "other_total": str(other),
        "sample": [
            {
                "source_invoice_id": r.get("source_invoice_id"),
                "source_document_number": r.get("source_document_number"),
                "source_series": r.get("source_series"),
                "source_access_key": r.get("source_access_key"),
                "source_xml_imported_in_erp": bool(r.get("source_xml_imported_in_erp")),
                "source_freight_amount": str(r.get("source_freight_amount")),
                "source_insurance_amount": str(r.get("source_insurance_amount")),
                "source_other_expenses": str(r.get("source_other_expenses")),
                "source_total_amount": str(r.get("source_total_amount")),
            }
            for r in rows
        ],
    }
    ds.close()
    print(json.dumps(out, indent=2, default=str))
    return out


async def pg_snapshot(label: str) -> dict:
    day_d = date.fromisoformat(DAY)
    async with AsyncSessionLocal() as db:
        inv = (
            await db.execute(
                text(
                    """
                    SELECT source_invoice_id, source_document_number, source_series,
                           access_key, LENGTH(access_key) AS key_len,
                           xml_imported_in_erp,
                           freight_amount, insurance_amount, other_expenses_amount,
                           total_amount, source_record_hash, last_sync_run_id
                    FROM fuel_purchase_invoices
                    WHERE entry_date = :day
                    ORDER BY source_invoice_id
                    """
                ),
                {"day": day_d},
            )
        )
        invoices = [dict(r._mapping) for r in inv]
        dups = (
            await db.execute(
                text(
                    """
                    SELECT access_key, COUNT(*) AS cnt
                    FROM fuel_purchase_invoices
                    WHERE access_key IS NOT NULL
                    GROUP BY access_key
                    HAVING COUNT(*) > 1
                    """
                )
            )
        ).fetchall()
        orphans = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM fuel_purchase_items i
                    LEFT JOIN fuel_purchase_invoices inv ON inv.id = i.purchase_invoice_id
                    WHERE inv.id IS NULL
                    """
                )
            )
        ).scalar_one()
        titles_unlinked = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM accounts_payable_titles t
                    WHERE t.purchase_invoice_id IS NULL
                      AND t.due_date >= CAST(:day AS date)
                      AND t.due_date < CAST(:day AS date) + 1
                    """
                ),
                {"day": day_d},
            )
        ).scalar_one()
        metrics = (
            await db.execute(
                text(
                    """
                    SELECT business_date::text AS business_date,
                           commercial_delivered_cost::text,
                           average_delivered_cost_per_liter::text,
                           erp_recorded_cost::text,
                           freight_amount::text,
                           other_expenses_amount::text,
                           invoice_count, item_count
                    FROM fuel_purchase_daily_metrics
                    WHERE business_date = :day
                    """
                ),
                {"day": day_d},
            )
        ).mappings().all()
        metrics = [dict(m) for m in metrics]
        ck = (
            await db.execute(
                text(
                    """
                    SELECT d.code AS dataset_code,
                           c.watermark_value,
                           c.source_upper_bound,
                           c.last_success_at::text AS last_success_at,
                           c.updated_at::text AS updated_at
                    FROM erp_sync_checkpoints c
                    JOIN erp_datasets d ON d.id = c.erp_dataset_id
                    WHERE d.code = :code
                    ORDER BY c.updated_at DESC
                    LIMIT 5
                    """
                ),
                {"code": DATASET},
            )
        ).mappings().all()
        items_day = (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM fuel_purchase_items i
                    JOIN fuel_purchase_invoices inv ON inv.id = i.purchase_invoice_id
                    WHERE inv.entry_date = :day
                    """
                ),
                {"day": day_d},
            )
        ).scalar_one()

    out = {
        "label": label,
        "invoices": [{k: (str(v) if v is not None else None) for k, v in row.items()} for row in invoices],
        "dup_access_keys": [{"access_key": r[0], "cnt": r[1]} for r in dups],
        "orphan_items": orphans,
        "titles_unlinked_day": titles_unlinked,
        "items_day": items_day,
        "metrics": metrics,
        "checkpoints": [dict(r) for r in ck],
        "with_key": sum(1 for i in invoices if i.get("access_key")),
        "without_key": sum(1 for i in invoices if not i.get("access_key")),
        "imported_xml": sum(1 for i in invoices if i.get("xml_imported_in_erp") in (True, "True", "true")),
        "freight_total": str(sum((Decimal(str(i.get("freight_amount") or 0)) for i in invoices), Decimal("0"))),
        "insurance_total": str(
            sum((Decimal(str(i.get("insurance_amount") or 0)) for i in invoices), Decimal("0"))
        ),
        "other_total": str(
            sum((Decimal(str(i.get("other_expenses_amount") or 0)) for i in invoices), Decimal("0"))
        ),
        "invalid_keys": [
            i["access_key"]
            for i in invoices
            if i.get("access_key") and (len(i["access_key"]) != 44 or not i["access_key"].isdigit())
        ],
    }
    print(json.dumps(out, indent=2, default=str))
    return out


async def async_main() -> None:
    print("=== PRE-PROBE XPERT ===")
    probe = await probe_xpert()
    assert probe["contract_valid"], probe
    assert probe["unique_invoice_ids"] == probe["query_rows"], probe["dup_invoice_ids"]
    assert not probe["dup_invoice_ids"], probe["dup_invoice_ids"]
    assert not probe["dup_keys"], probe["dup_keys"]
    assert not probe["bad_keys"], probe["bad_keys"]
    assert probe["branches"] == ["2443"], probe["branches"]
    assert probe["query_rows"] == probe["raw_comprovantes"], (
        probe["query_rows"],
        probe["raw_comprovantes"],
    )
    # Perfil atual XPERT 09/07/2443 (SAIDAS 1,9,21): 3 notas, todas com chave, 2 IMPORTOU_XML.
    # Homologação anterior citava 4/3/1 — a 4ª não está no filtro atual do dia.
    assert probe["query_rows"] == 3, f"expected 3 notes in current XPERT day, got {probe['query_rows']}"
    assert probe["with_key"] == 3 and probe["without_key"] == 0, probe
    assert probe["imported_xml_flag"] == 2, probe
    assert probe["unique_invoice_ids"] == 3
    assert not probe["dup_invoice_ids"]
    assert not probe["multi_compentradas"]

    print("=== CHECKPOINT / PG BEFORE ===")
    before = await pg_snapshot("before")

    client = httpx.Client(base_url="http://localhost:8000/api/v1", timeout=300.0)
    token = client.post(
        "/auth/login", json={"email": "admin@test.com", "password": "SenhaSegura123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    datasets = client.get("/integrations/xpert/datasets", headers=headers).json()
    by_code = {d["code"]: d for d in datasets}
    ds = by_code[DATASET]
    source_id = client.get("/integrations/xpert/sources", headers=headers).json()[0]["id"]

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
    print("validate", validate.status_code, validate.json())
    validate.raise_for_status()
    vj = validate.json()
    status = vj.get("status") or vj.get("contract_status")
    assert status == "VALID" or vj.get("valid") is True, vj

    def enqueue() -> dict:
        sync = client.post(
            "/integrations/xpert/sync-runs",
            headers=headers,
            json={
                "source_id": source_id,
                "dataset_codes": [DATASET],
                "station_ids": [STATION],
                "sync_mode": "INCREMENTAL_TIMESTAMP",
                "unsafe_homologation_acknowledged": True,
                "history_start_date": DAY,
                "history_end_date": DAY,
            },
        )
        print("enqueue", sync.status_code, sync.text[:500])
        sync.raise_for_status()
        run_id = sync.json()["runs"][0]["id"]
        return wait_run(client, headers, run_id)

    print("=== PASS 1 ===")
    run1 = enqueue()
    after1 = await pg_snapshot("after_pass1")

    print("=== PASS 2 ===")
    run2 = enqueue()
    after2 = await pg_snapshot("after_pass2")

    report = {
        "probe": probe,
        "validate": vj,
        "before": {
            "checkpoints": before.get("checkpoints"),
            "metrics": before.get("metrics"),
            "items_day": before.get("items_day"),
        },
        "run1": {
            "id": run1.get("id"),
            "status": run1.get("status"),
            "rows_read": run1.get("rows_read"),
            "rows_inserted": run1.get("rows_inserted"),
            "rows_updated": run1.get("rows_updated"),
            "rows_unchanged": run1.get("rows_unchanged"),
            "rows_error": run1.get("rows_error"),
            "query_hash": run1.get("query_hash"),
            "checkpoint_before": run1.get("checkpoint_before"),
            "checkpoint_after": run1.get("checkpoint_after"),
        },
        "run2": {
            "id": run2.get("id"),
            "status": run2.get("status"),
            "rows_read": run2.get("rows_read"),
            "rows_inserted": run2.get("rows_inserted"),
            "rows_updated": run2.get("rows_updated"),
            "rows_unchanged": run2.get("rows_unchanged"),
            "rows_error": run2.get("rows_error"),
            "checkpoint_before": run2.get("checkpoint_before"),
            "checkpoint_after": run2.get("checkpoint_after"),
        },
        "after_pass1": after1,
        "after_pass2": after2,
        "integrity": {
            "dup_access_keys": after2["dup_access_keys"],
            "orphan_items": after2["orphan_items"],
            "titles_unlinked_day": after2["titles_unlinked_day"],
            "invalid_keys": after2["invalid_keys"],
            "metrics_before": before.get("metrics"),
            "metrics_after": after2.get("metrics"),
            "items_before": before.get("items_day"),
            "items_after": after2.get("items_day"),
        },
        "note": (
            "XPERT atual 09/07/2443 SAIDAS IN (1,9,21) retorna 3 notas (todas com chave). "
            "Perfil esperado antigo 4/3/1 não se reproduz na fonte agora."
        ),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print("wrote", OUT)


def main() -> None:
    import asyncio

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
