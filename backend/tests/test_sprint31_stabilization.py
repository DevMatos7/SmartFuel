"""Testes Sprint 3.1 — estabilização da central de cotações."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.quote import Quote
from app.services.quote_expiration_service import QUOTE_EXPIRATION_ADVISORY_LOCK_KEY, QuoteExpirationService
from app.services.quote_service import QuoteService
from app.storage.object_storage import ObjectStorageService
from tests.test_sprint3_quotes import (
    _add_item,
    _create_draft_quote,
    _upload_evidence,
)

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture
async def master_context(db_session, org, auth_headers, client, headquarters):
    from factories import seed_master_data
    from tests.test_sprint3_quotes import _create_distributor

    await seed_master_data(db_session, org.id)
    await db_session.flush()
    distributor = await _create_distributor(client, auth_headers)
    products = await client.get("/api/v1/products", headers=auth_headers)
    terms = await client.get("/api/v1/payment-terms", headers=auth_headers)
    assert products.status_code == 200
    assert terms.status_code == 200
    return {
        "station_id": str(headquarters.id),
        "distributor_id": distributor["id"],
        "product_id": products.json()["items"][0]["id"],
        "payment_term_id": terms.json()["items"][0]["id"],
    }


async def _activate_quote(client, headers, quote_id: str, version: int) -> dict:
    response = await client.post(
        f"/api/v1/quotes/{quote_id}/activate",
        headers=headers,
        json={"expected_version": version},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_item_effective_status_partial_expiry(
    client, auth_headers, master_context, db_session
) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
        price="5.3400",
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    terms = await client.get("/api/v1/payment-terms", headers=auth_headers)
    second_term = terms.json()["items"][1]["id"]
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=second_term,
        price="5.3600",
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    db_quote = await db_session.get(Quote, uuid.UUID(active["id"]))
    assert db_quote is not None
    from app.models.quote_item import QuoteItem

    item_result = await db_session.execute(
        select(QuoteItem).where(QuoteItem.quote_id == db_quote.id).order_by(QuoteItem.sequence)
    )
    items = list(item_result.scalars().all())
    future = datetime.now(UTC) + timedelta(hours=3)
    items[0].valid_until = datetime.now(UTC) - timedelta(minutes=5)
    items[1].valid_until = future
    db_quote.valid_until = future
    await db_session.flush()

    refreshed = await client.get(f"/api/v1/quotes/{active['id']}", headers=auth_headers)
    body = refreshed.json()
    assert body["status"] == "ACTIVE"
    assert body["effective_status"] == "ACTIVE"
    assert body["items"][0]["item_effective_status"] == "EXPIRED"
    assert body["items"][1]["item_effective_status"] == "ACTIVE"


async def test_quote_expires_when_all_items_expired(client, auth_headers, master_context, db_session) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    db_quote = await db_session.get(Quote, uuid.UUID(active["id"]))
    past = datetime.now(UTC) - timedelta(minutes=1)
    future = datetime.now(UTC) + timedelta(hours=2)
    db_quote.valid_until = future
    from app.models.quote_item import QuoteItem

    item_result = await db_session.execute(
        select(QuoteItem).where(QuoteItem.quote_id == db_quote.id)
    )
    item = item_result.scalar_one()
    item.valid_until = past
    await db_session.flush()

    refreshed = await client.get(f"/api/v1/quotes/{active['id']}", headers=auth_headers)
    assert refreshed.json()["effective_status"] == "EXPIRED"


async def test_duplicate_without_copy_evidences(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    now = datetime.now(UTC)
    dup = await client.post(
        f"/api/v1/quotes/{active['id']}/duplicate",
        headers=auth_headers,
        json={
            "target_station_id": master_context["station_id"],
            "quoted_at": now.isoformat(),
            "valid_until": (now + timedelta(hours=4)).isoformat(),
            "copy_evidences": False,
        },
    )
    assert dup.status_code == 201, dup.text
    assert dup.json()["evidences"] == []


async def test_duplicate_with_copy_evidences(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    now = datetime.now(UTC)
    dup = await client.post(
        f"/api/v1/quotes/{active['id']}/duplicate",
        headers=auth_headers,
        json={
            "target_station_id": master_context["station_id"],
            "quoted_at": now.isoformat(),
            "valid_until": (now + timedelta(hours=4)).isoformat(),
            "copy_evidences": True,
        },
    )
    assert dup.status_code == 201, dup.text
    draft = dup.json()
    assert draft["status"] == "DRAFT"
    assert len(draft["evidences"]) == 1
    assert draft["evidences"][0]["sha256"] == active["evidences"][0]["sha256"]


async def test_expiration_lock_skips_concurrent_run(db_engine) -> None:
    async with db_engine.connect() as holder:
        await holder.execute(
            text("SELECT pg_advisory_lock(:key)"),
            {"key": QUOTE_EXPIRATION_ADVISORY_LOCK_KEY},
        )
        async with db_engine.connect() as runner:
            session = AsyncSession(bind=runner, expire_on_commit=False)
            service = QuoteExpirationService(session)
            result = await service.run(origin="TEST")
            assert result["skipped"] is True
            assert result["expired_count"] == 0
            await session.close()
        await holder.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": QUOTE_EXPIRATION_ADVISORY_LOCK_KEY},
        )


async def test_active_quote_immutability_endpoints(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    item = await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    patch = await client.patch(
        f"/api/v1/quotes/{active['id']}",
        headers=auth_headers,
        json={"expected_version": active["version"], "notes": "tentativa"},
    )
    assert patch.status_code == 400
    assert patch.json()["error"]["code"] == "QUOTE_NOT_EDITABLE"

    add_item = await client.post(
        f"/api/v1/quotes/{active['id']}/items",
        headers=auth_headers,
        json={
            "expected_version": active["version"],
            "product_id": master_context["product_id"],
            "payment_term_id": master_context["payment_term_id"],
            "quoted_price_per_liter": "5.5000",
            "minimum_volume_liters": "5000.000",
        },
    )
    assert add_item.status_code == 400

    delete_item = await client.delete(
        f"/api/v1/quotes/{active['id']}/items/{item['id']}?expected_version={active['version']}",
        headers=auth_headers,
    )
    assert delete_item.status_code == 400

    evidence_id = active["evidences"][0]["id"]
    delete_ev = await client.delete(
        f"/api/v1/quotes/{active['id']}/evidences/{evidence_id}?expected_version={active['version']}",
        headers=auth_headers,
    )
    assert delete_ev.status_code == 400


async def test_concurrent_quote_numbers(client, auth_headers, master_context) -> None:
    numbers: list[int] = []
    for _ in range(5):
        quote = await _create_draft_quote(
            client, auth_headers, master_context["station_id"], master_context["distributor_id"]
        )
        numbers.append(quote["quote_number"])
    assert len(numbers) == len(set(numbers))
    assert numbers == sorted(numbers)


async def test_storage_rejects_fallback_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "object_storage_allow_memory_fallback", False)
    storage = ObjectStorageService()
    storage._client = None

    class BrokenMinio:
        def bucket_exists(self, _bucket: str) -> bool:
            raise Exception("down")

    storage._client = BrokenMinio()  # type: ignore[assignment]

    from app.core.exceptions import AppError

    with pytest.raises(AppError) as exc:
        storage.put_object(key="k", data=b"x", content_type="application/pdf")
    assert exc.value.code == "STORAGE_UNAVAILABLE"


async def test_revision_activation_supersedes_original(client, auth_headers, master_context) -> None:
    quote = await _create_draft_quote(
        client, auth_headers, master_context["station_id"], master_context["distributor_id"]
    )
    await _add_item(
        client,
        auth_headers,
        quote["id"],
        version=quote["version"],
        product_id=master_context["product_id"],
        payment_term_id=master_context["payment_term_id"],
    )
    quote = (await client.get(f"/api/v1/quotes/{quote['id']}", headers=auth_headers)).json()
    quote = await _upload_evidence(client, auth_headers, quote["id"], quote["version"])
    active = await _activate_quote(client, auth_headers, quote["id"], quote["version"])

    revise = await client.post(
        f"/api/v1/quotes/{active['id']}/revise",
        headers=auth_headers,
        json={"reason": "Correção de preço"},
    )
    assert revise.status_code == 201
    draft = revise.json()
    assert draft["status"] == "DRAFT"
    assert draft["replaces_quote_id"] == active["id"]

    draft = await _upload_evidence(client, auth_headers, draft["id"], draft["version"])

    original = await client.get(f"/api/v1/quotes/{active['id']}", headers=auth_headers)
    assert original.json()["status"] == "ACTIVE"

    activated_revision = await _activate_quote(client, auth_headers, draft["id"], draft["version"])
    assert activated_revision["status"] == "ACTIVE"

    original_after = await client.get(f"/api/v1/quotes/{active['id']}", headers=auth_headers)
    assert original_after.json()["status"] == "SUPERSEDED"
    assert original_after.json()["superseded_by_quote_id"] == draft["id"]
