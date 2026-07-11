"""Sprint 8.2 Etapa A — sync manual 7 dias (03/07/2026–09/07/2026) filial 2443.

Ordem: INVOICES → ITEMS → AP → reconcile títulos → agregações → pass 2.

Uso (host, API :8000, worker ativo):
  python scripts/homolog_sprint82_sync_7d.py
"""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import func, select, text

from app.core.database import AsyncSessionLocal
from app.core.fuel_purchases_enums import InvoiceLinkStatus, PurchaseMetricExclusionReason
from app.core.master_data_enums import MappingStatus
from app.integrations.xpert.direct_sqlserver import DirectSqlServerDataSource
from app.integrations.xpert.query_guard import current_query_hash
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncCheckpoint, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_purchases import (
    AccountsPayableTitle,
    FuelPurchaseInvoice,
    FuelPurchaseItem,
)
from app.models.product import Product
from app.services.fuel_purchase_aggregation_service import (
    FuelPurchaseAggregationService,
    PurchaseAggregationKey,
)
from app.services.fuel_purchases_apply_service import LITER_UNITS
from app.core.fuel_purchases_normalization import delivered_cost_per_liter

BASE = "http://localhost:8000/api/v1"
STATION = "1edc5c8b-0ba1-405c-a000-03e61e31521e"
BRANCH = 2443
DATE_FROM = date(2026, 7, 3)
DATE_TO = date(2026, 7, 9)  # inclusivo → history_end_date
DATASETS = [
    "FUEL_PURCHASE_INVOICES",
    "FUEL_PURCHASE_ITEMS",
    "ACCOUNTS_PAYABLE_TITLES",
]
EMAIL = "admin@test.com"
PASSWORD = "SenhaSegura123"

# Canônicos esperados (código seed)
FUEL_MAP = {
    "1": "ETANOL_HIDRATADO",  # ETANOL COMUM
    "2": "GASOLINA_C_COMUM",  # GASOLINA COMUM
    "4": "DIESEL_B_S10_COMUM",  # DIESEL S10 COMUM
    "1272": "ETANOL_HIDRATADO",  # ETANOL ADITIVADO — validar; usa variante COMMON se não houver aditivado etanol seed
    "1271": "GASOLINA_C_ADITIVADA",  # GASOLINA ADITIVADA
}
IGNORE_PRODUCTS = {
    "1505": "NON_FUEL_MERCHANDISE — ADITIVO FLEX 200ML BARDAHL",
    "1506": "NON_FUEL_MERCHANDISE — FLUIDO PARA RADIADOR ROSA 1L BARDAHL",
}


def _out_dir() -> Path:
    for root in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        if (root / "docs").is_dir():
            out = root / "docs" / "sprints"
            out.mkdir(parents=True, exist_ok=True)
            return out
    p = Path("/tmp/sprint-docs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def wait_run(client: httpx.Client, headers: dict, run_id: str) -> dict:
    for _ in range(240):
        run = client.get(f"/integrations/xpert/sync-runs/{run_id}", headers=headers).json()
        print(
            run.get("dataset_code"),
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
            "cp_before",
            run.get("checkpoint_before"),
            "cp_after",
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


def sync_one(
    client: httpx.Client,
    headers: dict,
    *,
    source_id: str,
    code: str,
) -> dict:
    sync = client.post(
        "/integrations/xpert/sync-runs",
        headers=headers,
        json={
            "source_id": source_id,
            "dataset_codes": [code],
            "station_ids": [STATION],
            "sync_mode": "INCREMENTAL_TIMESTAMP",
            "unsafe_homologation_acknowledged": True,
            "history_start_date": DATE_FROM.isoformat(),
            "history_end_date": DATE_TO.isoformat(),
        },
    )
    print("enqueue", code, sync.status_code, sync.text[:400])
    sync.raise_for_status()
    run_id = sync.json()["runs"][0]["id"]
    return wait_run(client, headers, run_id)


async def xpert_counts(db) -> dict:
    source = (await db.execute(select(ErpSource).limit(1))).scalar_one()
    ds = DirectSqlServerDataSource(source)
    conn = ds._connect()  # noqa: SLF001
    cur = conn.cursor()
    start = DATE_FROM.isoformat()
    end_excl = (DATE_TO + timedelta(days=1)).isoformat()
    try:
        cur.execute(
            f"""
            SELECT COUNT(*) FROM COMPROVANTES C
            WHERE C.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            """
        )
        inv = int(cur.fetchone()[0])
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM ITENSMOVPRODUTOS I
            INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
            INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
            WHERE I.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            """
        )
        items = int(cur.fetchone()[0])
        cur.execute(
            f"""
            SELECT COUNT(*) FROM CONTASPAGAR CP
            WHERE CP.ID_FILIAL={BRANCH}
              AND CP.DTACONTA >= '{start}' AND CP.DTACONTA < '{end_excl}'
            """
        )
        titles = int(cur.fetchone()[0])
        cur.execute(
            f"""
            SELECT
              CAST(SUM(CASE WHEN UPPER(P.UNIDADE) IN ('L','LT','LITRO','LITROS','LITER','LITERS') THEN I.QTDE ELSE 0 END) AS DECIMAL(18,3)),
              CAST(SUM(I.TOTAL) AS DECIMAL(18,2))
            FROM ITENSMOVPRODUTOS I
            INNER JOIN MOVPRODUTOS M ON I.ID_MOVPRODUTOS=M.ID_MOVPRODUTOS AND I.ID_FILIAL=M.ID_FILIAL AND I.ID_DB=M.ID_DB
            INNER JOIN COMPROVANTES C ON C.ID_COMPROVANTE=M.ID_COMPROVANTE AND C.ID_FILIAL=M.ID_FILIAL AND C.ID_DB=M.ID_DB
            INNER JOIN PRODUTOS P ON P.ID_PRODUTOS=I.ID_PRODUTOS AND P.ID_FILIAL=I.ID_FILIAL
            WHERE I.ID_FILIAL={BRANCH} AND C.SAIDAS_ENTRADAS IN (1,9,21)
              AND C.DTACONTA >= '{start}' AND C.DTACONTA < '{end_excl}'
            """
        )
        vol_val = cur.fetchone()
        # cadastro combustível
        cur.execute(
            f"""
            SELECT CAST(P.ID_PRODUTOS AS VARCHAR(20)), CAST(P.NOMEPRODUTO AS VARCHAR(120)),
                   CAST(P.UNIDADE AS VARCHAR(20)), CAST(P.ID_FILIAL AS VARCHAR(20))
            FROM PRODUTOS P
            WHERE P.ID_FILIAL={BRANCH} AND P.ID_PRODUTOS IN (1,2,4,1271,1272,1505,1506)
            ORDER BY P.ID_PRODUTOS
            """
        )
        products = [
            {"erp_id": r[0], "name": r[1], "unit": r[2], "branch": r[3]} for r in cur.fetchall()
        ]
        return {
            "invoices": inv,
            "items": items,
            "titles": titles,
            "volume_lt": str(vol_val[0] or 0),
            "items_total_value": str(vol_val[1] or 0),
            "products_cadastro": products,
        }
    finally:
        ds.close()


async def pg_counts(db) -> dict:
    inv = (
        await db.execute(
            select(func.count())
            .select_from(FuelPurchaseInvoice)
            .where(
                FuelPurchaseInvoice.station_id == STATION,
                FuelPurchaseInvoice.entry_date >= DATE_FROM,
                FuelPurchaseInvoice.entry_date <= DATE_TO,
            )
        )
    ).scalar_one()
    items = (
        await db.execute(
            select(func.count())
            .select_from(FuelPurchaseItem)
            .where(
                FuelPurchaseItem.station_id == STATION,
                FuelPurchaseItem.purchase_invoice_id.in_(
                    select(FuelPurchaseInvoice.id).where(
                        FuelPurchaseInvoice.station_id == STATION,
                        FuelPurchaseInvoice.entry_date >= DATE_FROM,
                        FuelPurchaseInvoice.entry_date <= DATE_TO,
                    )
                ),
            )
        )
    ).scalar_one()
    titles = (
        await db.execute(
            select(func.count())
            .select_from(AccountsPayableTitle)
            .where(
                AccountsPayableTitle.station_id == STATION,
                AccountsPayableTitle.issue_date >= DATE_FROM,
                AccountsPayableTitle.issue_date <= DATE_TO,
            )
        )
    ).scalar_one()
    # fallback titles by entry if issue_date null — use accounting_date if exists
    return {"invoices": int(inv), "items": int(items), "titles": int(titles)}


async def preflight(db) -> dict:
    datasets = list((await db.execute(select(ErpDataset).where(ErpDataset.code.in_(DATASETS)))).scalars().all())
    ds_info = []
    for d in datasets:
        live_hash = current_query_hash(d.query_file)
        cp = (
            await db.execute(
                select(ErpSyncCheckpoint).where(
                    ErpSyncCheckpoint.erp_dataset_id == d.id,
                    ErpSyncCheckpoint.station_id == STATION,
                )
            )
        ).scalar_one_or_none()
        last_run = (
            await db.execute(
                select(ErpSyncRun)
                .where(ErpSyncRun.erp_dataset_id == d.id, ErpSyncRun.station_id == STATION)
                .order_by(ErpSyncRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        ds_info.append(
            {
                "code": d.code,
                "contract_status": d.contract_status,
                "query_file": d.query_file,
                "query_hash_stored": d.query_hash,
                "query_hash_live": live_hash,
                "query_hash_match": d.query_hash == live_hash,
                "normalization_version_last_run": last_run.normalization_version if last_run else None,
                "hash_schema_version_last_run": last_run.hash_schema_version if last_run else None,
                "overlap_seconds": d.overlap_seconds,
                "schedule_enabled": d.schedule_enabled,
                "enabled": d.enabled,
                "checkpoint_id": str(cp.id) if cp else None,
                "checkpoint_watermark": cp.watermark_value if cp else None,
                "checkpoint_last_success_at": cp.last_success_at.isoformat()
                if cp and cp.last_success_at
                else None,
                "note": "Janela histórica explícita NÃO avança checkpoint",
            }
        )
    xpert = await xpert_counts(db)
    pg = await pg_counts(db)
    return {"datasets": ds_info, "xpert": xpert, "postgres_before": pg}


async def post_metrics(db) -> dict:
    invs = list(
        (
            await db.execute(
                select(FuelPurchaseInvoice).where(
                    FuelPurchaseInvoice.station_id == STATION,
                    FuelPurchaseInvoice.entry_date >= DATE_FROM,
                    FuelPurchaseInvoice.entry_date <= DATE_TO,
                )
            )
        )
        .scalars()
        .all()
    )
    inv_ids = [i.id for i in invs]
    items = []
    if inv_ids:
        items = list(
            (
                await db.execute(
                    select(FuelPurchaseItem).where(FuelPurchaseItem.purchase_invoice_id.in_(inv_ids))
                )
            )
            .scalars()
            .all()
        )
    titles = list(
        (
            await db.execute(
                select(AccountsPayableTitle).where(
                    AccountsPayableTitle.station_id == STATION,
                    AccountsPayableTitle.issue_date >= DATE_FROM,
                    AccountsPayableTitle.issue_date <= DATE_TO,
                )
            )
        )
        .scalars()
        .all()
    )

    leak = sum(1 for i in invs if getattr(i, "source_branch_id", None) not in (None, str(BRANCH), BRANCH))
    # branch guard stores on staging; invoices don't have source_branch — check via raw if needed
    cancelled = sum(1 for i in invs if i.is_cancelled)
    returns = sum(1 for i in invs if i.operation_type == "PURCHASE_RETURN")
    mapped = sum(1 for i in items if i.canonical_product_id)
    vol_lt = sum((i.volume_liters or Decimal(0) for i in items), Decimal(0))
    cost = sum((i.commercial_delivered_cost or Decimal(0) for i in items), Decimal(0))
    units = {}
    for i in items:
        u = (i.source_unit or "").strip() or "(vazio)"
        units[u] = units.get(u, 0) + 1
    link = {}
    for t in titles:
        link[t.invoice_link_status] = link.get(t.invoice_link_status, 0) + 1
    excl = {}
    for i in items:
        for r in i.metric_exclusion_reasons or []:
            code = r if isinstance(r, str) else (r.get("code") if isinstance(r, dict) else str(r))
            excl[code] = excl.get(code, 0) + 1

    return {
        "invoices": len(invs),
        "items": len(items),
        "titles_in_window_or_station": len(titles),
        "cancelled_invoices": cancelled,
        "returns": returns,
        "items_mapped": mapped,
        "volume_liters_sum": str(vol_lt),
        "commercial_delivered_cost_sum": str(cost),
        "source_units": units,
        "title_link_status": link,
        "exclusion_reason_counts": excl,
        "documents": [i.source_document_number for i in invs],
    }


async def zero_overlap(db) -> list[dict]:
    """Evita puxar dia anterior via overlap na janela histórica explícita."""
    changed = []
    for code in DATASETS:
        ds = (await db.execute(select(ErpDataset).where(ErpDataset.code == code))).scalar_one()
        before = ds.overlap_seconds
        ds.schedule_enabled = False
        ds.enabled = True
        if ds.overlap_seconds != 0:
            ds.overlap_seconds = 0
        changed.append({"code": code, "overlap_before": before, "overlap_after": ds.overlap_seconds})
    await db.commit()
    return changed


async def restore_overlap(db, snapshot: list[dict]) -> None:
    for row in snapshot:
        ds = (await db.execute(select(ErpDataset).where(ErpDataset.code == row["code"]))).scalar_one()
        ds.overlap_seconds = row["overlap_before"]
    await db.commit()


async def validate_and_map_products(client: httpx.Client, headers: dict, db) -> dict:
    # Validação cadastral XPERT já em preflight; aqui aplica ignore/map no PG
    erp_rows = list(
        (
            await db.execute(
                select(ErpProduct).where(
                    ErpProduct.station_id == STATION,
                    ErpProduct.erp_product_id.in_(list(FUEL_MAP) + list(IGNORE_PRODUCTS)),
                )
            )
        )
        .scalars()
        .all()
    )
    by_erp = {e.erp_product_id: e for e in erp_rows}
    products = list((await db.execute(select(Product))).scalars().all())
    by_code = {p.code: p for p in products}

    result = {"ignored": [], "mapped": [], "missing_erp": [], "validation": []}

    # Validação textual dos combustíveis
    for erp_id, canon_code in FUEL_MAP.items():
        e = by_erp.get(erp_id)
        if e is None:
            result["missing_erp"].append(erp_id)
            continue
        unit = (e.erp_unit or "").upper()
        result["validation"].append(
            {
                "erp_product_id": erp_id,
                "description": e.erp_description,
                "unit": e.erp_unit,
                "unit_is_lt": unit in {"L", "LT", "LITRO", "LITROS", "LITER", "LITERS"},
                "proposed_canonical": canon_code,
                "canonical_exists": canon_code in by_code,
            }
        )

    for erp_id, reason in IGNORE_PRODUCTS.items():
        e = by_erp.get(erp_id)
        if e is None:
            result["missing_erp"].append(erp_id)
            continue
        if e.mapping_status == MappingStatus.IGNORED:
            result["ignored"].append({"erp_product_id": erp_id, "status": "already_ignored"})
            continue
        resp = client.post(
            f"/master-data/erp-products/{e.id}/ignore",
            headers=headers,
            json={"reason": reason},
        )
        # path may be /erp-products
        if resp.status_code == 404:
            resp = client.post(
                f"/erp-products/{e.id}/ignore",
                headers=headers,
                json={"reason": reason},
            )
        result["ignored"].append(
            {"erp_product_id": erp_id, "http": resp.status_code, "body": resp.text[:300]}
        )

    for erp_id, canon_code in FUEL_MAP.items():
        e = by_erp.get(erp_id)
        canon = by_code.get(canon_code)
        if e is None or canon is None:
            continue
        unit = (e.erp_unit or "").upper()
        if unit not in {"L", "LT", "LITRO", "LITROS", "LITER", "LITERS"}:
            result["mapped"].append({"erp_product_id": erp_id, "skipped": "unit_not_lt", "unit": e.erp_unit})
            continue
        if e.mapping_status == MappingStatus.MAPPED and e.canonical_product_id == canon.id:
            result["mapped"].append({"erp_product_id": erp_id, "status": "already_mapped"})
            continue
        payload = {
            "canonical_product_id": str(canon.id),
            "reason": f"Sprint 8.2 — {e.erp_description} ({e.erp_unit}) → {canon_code}",
        }
        resp = client.post(f"/erp-products/{e.id}/map", headers=headers, json=payload)
        if resp.status_code == 404:
            resp = client.post(
                f"/master-data/erp-products/{e.id}/map", headers=headers, json=payload
            )
        result["mapped"].append(
            {
                "erp_product_id": erp_id,
                "canonical": canon_code,
                "http": resp.status_code,
                "body": resp.text[:300],
            }
        )
    return result


async def reconcile_purchase_items_after_mapping(db) -> dict:
    """Atualiza canonical/elegibilidade/volume nos itens — sync não altera se hash origem igual."""
    from app.core.fuel_purchases_enums import PurchaseMetricEligibilityStatus

    items = list(
        (
            await db.execute(
                select(FuelPurchaseItem).where(FuelPurchaseItem.station_id == STATION)
            )
        )
        .scalars()
        .all()
    )
    updated = 0
    keys: list[PurchaseAggregationKey] = []
    for item in items:
        erp = None
        if item.source_product_id:
            erp = (
                await db.execute(
                    select(ErpProduct).where(
                        ErpProduct.station_id == STATION,
                        ErpProduct.erp_product_id == item.source_product_id,
                    )
                )
            ).scalar_one_or_none()
        if erp is None:
            continue

        old_canon = item.canonical_product_id
        unit = (item.source_unit or "").strip().lower()
        qty = item.source_quantity or Decimal(0)
        volume = item.volume_liters
        reasons: list[str] = []

        if erp.mapping_status == MappingStatus.IGNORED:
            item.canonical_product_id = None
            item.erp_product_id = erp.id
            reasons.append(PurchaseMetricExclusionReason.IGNORED_PRODUCT.value)
            if unit not in LITER_UNITS:
                volume = None
                reasons.append(PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value)
            item.volume_liters = volume
            item.delivered_cost_per_liter = delivered_cost_per_liter(
                commercial_cost=item.commercial_delivered_cost, volume_liters=volume
            )
            item.metric_eligibility_status = PurchaseMetricEligibilityStatus.EXCLUDED.value
            item.metric_exclusion_reasons = reasons
            updated += 1
        elif erp.mapping_status == MappingStatus.MAPPED and erp.canonical_product_id:
            item.canonical_product_id = erp.canonical_product_id
            item.erp_product_id = erp.id
            if unit in LITER_UNITS:
                volume = qty
                item.volume_liters = volume
            else:
                volume = None
                reasons.append(PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value)
                item.volume_liters = None
            item.delivered_cost_per_liter = delivered_cost_per_liter(
                commercial_cost=item.commercial_delivered_cost, volume_liters=volume
            )
            if item.is_cancelled:
                reasons.append(PurchaseMetricExclusionReason.CANCELLED_INVOICE.value)
            if volume is None or volume <= 0:
                if PurchaseMetricExclusionReason.UNIT_CONVERSION_REQUIRED.value not in reasons:
                    reasons.append(PurchaseMetricExclusionReason.INVALID_QUANTITY.value)
            if reasons:
                item.metric_eligibility_status = PurchaseMetricEligibilityStatus.EXCLUDED.value
                item.metric_exclusion_reasons = reasons
            else:
                item.metric_eligibility_status = PurchaseMetricEligibilityStatus.ELIGIBLE.value
                item.metric_exclusion_reasons = None
            updated += 1
        else:
            continue

        inv = (
            await db.execute(
                select(FuelPurchaseInvoice).where(FuelPurchaseInvoice.id == item.purchase_invoice_id)
            )
        ).scalar_one()
        keys.append(
            PurchaseAggregationKey(
                station_id=item.station_id,
                business_date=inv.entry_date,
                canonical_product_id=item.canonical_product_id,
                distributor_id=inv.distributor_id,
            )
        )
        if old_canon != item.canonical_product_id:
            keys.append(
                PurchaseAggregationKey(
                    station_id=item.station_id,
                    business_date=inv.entry_date,
                    canonical_product_id=old_canon,
                    distributor_id=inv.distributor_id,
                )
            )

    await db.flush()
    if items:
        agg = FuelPurchaseAggregationService(db)
        await agg.rebuild_keys(
            organization_id=items[0].organization_id, keys=keys, sync_run_id=None
        )
    await db.commit()
    return {"items_touched": updated, "aggregation_keys": len(keys)}


async def main_async() -> None:
    out_dir = _out_dir()
    report: dict = {
        "started_at": datetime.now(UTC).isoformat(),
        "window": {"from": DATE_FROM.isoformat(), "to": DATE_TO.isoformat(), "station": STATION, "branch": BRANCH},
    }

    client = httpx.Client(base_url=BASE, timeout=300.0)
    token = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    source_id = client.get("/integrations/xpert/sources", headers=headers).json()[0]["id"]

    async with AsyncSessionLocal() as db:
        overlap_snap = await zero_overlap(db)
        report["overlap_adjustment"] = overlap_snap
        report["preflight"] = await preflight(db)

    # Validar contratos via API
    datasets_api = {d["code"]: d for d in client.get("/integrations/xpert/datasets", headers=headers).json()}
    validations = {}
    for code in DATASETS:
        ds = datasets_api[code]
        client.patch(
            f"/integrations/xpert/datasets/{ds['id']}",
            headers=headers,
            json={"enabled": True, "schedule_enabled": False},
        )
        v = client.post(
            f"/integrations/xpert/datasets/{ds['id']}/validate-contract",
            headers=headers,
            params={"station_id": STATION},
        )
        validations[code] = {"http": v.status_code, "body": v.json() if v.headers.get("content-type", "").startswith("application/json") else v.text[:500]}
    report["contract_validation"] = validations

    # Pass 1
    print("=== PASS 1 ===")
    pass1 = {}
    for code in DATASETS:
        pass1[code] = sync_one(client, headers, source_id=source_id, code=code)
    report["pass1"] = {
        k: {
            "id": v.get("id"),
            "status": v.get("status"),
            "rows_read": v.get("rows_read"),
            "rows_inserted": v.get("rows_inserted"),
            "rows_updated": v.get("rows_updated"),
            "rows_unchanged": v.get("rows_unchanged"),
            "rows_error": v.get("rows_error"),
            "checkpoint_before": v.get("checkpoint_before"),
            "checkpoint_after": v.get("checkpoint_after"),
            "window_start": v.get("window_start"),
            "window_end": v.get("window_end"),
        }
        for k, v in pass1.items()
    }

    async with AsyncSessionLocal() as db:
        report["postgres_after_pass1"] = await post_metrics(db)
        # sync PRODUCTS if fuel erp missing
        missing = [
            pid
            for pid in list(FUEL_MAP) + list(IGNORE_PRODUCTS)
            if (
                await db.execute(
                    select(ErpProduct).where(
                        ErpProduct.station_id == STATION, ErpProduct.erp_product_id == pid
                    )
                )
            ).scalar_one_or_none()
            is None
        ]
        report["missing_erp_products_before_map"] = missing

    if report.get("missing_erp_products_before_map"):
        print("=== SYNC PRODUCTS (mestre) para mapear ===")
        # optional PRODUCTS dataset
        if "PRODUCTS" in datasets_api:
            sync_one(client, headers, source_id=source_id, code="PRODUCTS")

    async with AsyncSessionLocal() as db:
        report["mapping"] = await validate_and_map_products(client, headers, db)
        # refresh session after HTTP commits
    async with AsyncSessionLocal() as db:
        report["reconcile_mappings"] = await reconcile_purchase_items_after_mapping(db)
        report["postgres_after_mapping"] = await post_metrics(db)

    # Pass 2 idempotent
    print("=== PASS 2 IDEMPOTENT ===")
    pass2 = {}
    for code in DATASETS:
        pass2[code] = sync_one(client, headers, source_id=source_id, code=code)
    report["pass2"] = {
        k: {
            "id": v.get("id"),
            "status": v.get("status"),
            "rows_read": v.get("rows_read"),
            "rows_inserted": v.get("rows_inserted"),
            "rows_updated": v.get("rows_updated"),
            "rows_unchanged": v.get("rows_unchanged"),
            "rows_error": v.get("rows_error"),
            "checkpoint_before": v.get("checkpoint_before"),
            "checkpoint_after": v.get("checkpoint_after"),
        }
        for k, v in pass2.items()
    }

    async with AsyncSessionLocal() as db:
        report["postgres_final"] = await post_metrics(db)
        report["checkpoints_final"] = (await preflight(db))["datasets"]
        await restore_overlap(db, overlap_snap)

    report["finished_at"] = datetime.now(UTC).isoformat()
    out = out_dir / "sprint-08-2-etapa-a-sync-7d.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main_async())
