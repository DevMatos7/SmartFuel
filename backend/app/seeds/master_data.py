"""Seeds idempotentes de cadastros mestres por organização."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_term import PaymentTerm
from app.models.product import Product

PRODUCT_SEEDS = [
    {
        "code": "ETANOL_HIDRATADO",
        "name": "Etanol hidratado",
        "fuel_family": "ETHANOL",
        "commercial_variant": "COMMON",
        "display_order": 10,
    },
    {
        "code": "GASOLINA_C_COMUM",
        "name": "Gasolina C comum",
        "fuel_family": "GASOLINE_C",
        "commercial_variant": "COMMON",
        "display_order": 20,
    },
    {
        "code": "GASOLINA_C_ADITIVADA",
        "name": "Gasolina C aditivada",
        "fuel_family": "GASOLINE_C",
        "commercial_variant": "ADDITIVATED",
        "display_order": 30,
    },
    {
        "code": "DIESEL_B_S10_COMUM",
        "name": "Diesel B S10 comum",
        "fuel_family": "DIESEL_B_S10",
        "commercial_variant": "COMMON",
        "display_order": 40,
    },
    {
        "code": "DIESEL_B_S10_ADITIVADO",
        "name": "Diesel B S10 aditivado",
        "fuel_family": "DIESEL_B_S10",
        "commercial_variant": "ADDITIVATED",
        "display_order": 50,
    },
    {
        "code": "DIESEL_B_S500_COMUM",
        "name": "Diesel B S500 comum",
        "fuel_family": "DIESEL_B_S500",
        "commercial_variant": "COMMON",
        "display_order": 60,
    },
]

PAYMENT_TERM_SEEDS = [
    {"code": "CASH_0", "name": "À vista", "payment_type": "CASH", "days": 0},
    {"code": "TERM_7", "name": "Prazo 7 dias", "payment_type": "TERM", "days": 7},
    {"code": "TERM_15", "name": "Prazo 15 dias", "payment_type": "TERM", "days": 15},
    {"code": "TERM_21", "name": "Prazo 21 dias", "payment_type": "TERM", "days": 21},
    {"code": "TERM_30", "name": "Prazo 30 dias", "payment_type": "TERM", "days": 30},
    {"code": "ANTICIPATED_0", "name": "Antecipado", "payment_type": "ANTICIPATED", "days": 0},
]

VALID_FUEL_FAMILIES = frozenset({"ETHANOL", "GASOLINE_C", "DIESEL_B_S10", "DIESEL_B_S500"})
VALID_COMMERCIAL_VARIANTS = frozenset({"COMMON", "ADDITIVATED"})


async def seed_products_for_organization(session: AsyncSession, organization_id: uuid.UUID) -> int:
    created = 0
    for item in PRODUCT_SEEDS:
        existing = await session.execute(
            select(Product).where(
                Product.organization_id == organization_id,
                Product.code == item["code"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        session.add(
            Product(
                organization_id=organization_id,
                code=item["code"],
                name=item["name"],
                fuel_family=item["fuel_family"],
                commercial_variant=item["commercial_variant"],
                unit="LITER",
                purchasable=True,
                sellable=True,
                display_order=item["display_order"],
                active=True,
            )
        )
        created += 1
    await session.flush()
    return created


async def seed_payment_terms_for_organization(session: AsyncSession, organization_id: uuid.UUID) -> int:
    created = 0
    for item in PAYMENT_TERM_SEEDS:
        normalized = item["name"].upper()
        existing = await session.execute(
            select(PaymentTerm).where(
                PaymentTerm.organization_id == organization_id,
                PaymentTerm.code == item["code"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        session.add(
            PaymentTerm(
                organization_id=organization_id,
                code=item["code"],
                name=item["name"],
                normalized_name=normalized,
                payment_type=item["payment_type"],
                days=item["days"],
                active=True,
            )
        )
        created += 1
    await session.flush()
    return created


async def seed_master_data_for_organization(session: AsyncSession, organization_id: uuid.UUID) -> dict[str, int]:
    products = await seed_products_for_organization(session, organization_id)
    payment_terms = await seed_payment_terms_for_organization(session, organization_id)
    return {"products": products, "payment_terms": payment_terms}


DEFAULT_MINIMUM_VOLUME = Decimal("5000.000")
