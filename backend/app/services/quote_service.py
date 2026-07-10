from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.quote_enums import (
    EVIDENCE_REQUIRED_CHANNELS,
    FINAL_QUOTE_STATUSES,
    FreightCalculationType,
    FreightType,
    QuoteChangeAction,
    QuoteEntryMethod,
    QuoteSourceChannel,
    QuoteStatus,
)
from app.models.distribution_base import DistributionBase
from app.models.distributor import Distributor
from app.models.payment_term import PaymentTerm
from app.models.product import Product
from app.models.quote import Quote
from app.models.quote_evidence import QuoteEvidence
from app.models.quote_item import QuoteItem
from app.models.station import Station
from app.storage.object_storage import get_object_storage
from app.services.audit_service import AuditContext, AuditService
from app.services.distributor_service import DistributorService
from app.services.quote_history_service import QuoteHistoryService
from app.services.supplier_rule_service import SupplierRuleService


class QuoteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.history = QuoteHistoryService(db)
        self.distributor_service = DistributorService(db)
        self.supplier_rule_service = SupplierRuleService(db)

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _item_effective_valid_until(self, item: QuoteItem, quote: Quote) -> datetime:
        if item.valid_until is not None:
            return self._as_utc(item.valid_until)
        return self._as_utc(quote.valid_until)

    def compute_item_effective_status(
        self, item: QuoteItem, quote: Quote, *, now: datetime | None = None
    ) -> str:
        if quote.status in FINAL_QUOTE_STATUSES:
            return quote.status
        current = now or datetime.now(UTC)
        if self._item_effective_valid_until(item, quote) <= current:
            return QuoteStatus.EXPIRED
        return QuoteStatus.ACTIVE

    def compute_effective_status(self, quote: Quote, *, now: datetime | None = None) -> str:
        current = now or datetime.now(UTC)
        if quote.status in FINAL_QUOTE_STATUSES:
            return quote.status
        if quote.status == QuoteStatus.ACTIVE:
            header_expired = self._as_utc(quote.valid_until) <= current
            active_items = [item for item in quote.items if self._item_is_valid(item, quote, current)]
            if header_expired or not active_items:
                return QuoteStatus.EXPIRED
        return quote.status

    def _item_is_valid(self, item: QuoteItem, quote: Quote, now: datetime) -> bool:
        return self._item_effective_valid_until(item, quote) > now

    async def _next_quote_number(self, organization_id: uuid.UUID) -> int:
        result = await self.db.execute(
            text(
                """
                INSERT INTO organization_quote_counters (organization_id, next_number)
                VALUES (:organization_id, 2)
                ON CONFLICT (organization_id) DO UPDATE
                SET next_number = organization_quote_counters.next_number + 1
                RETURNING organization_quote_counters.next_number - 1
                """
            ),
            {"organization_id": organization_id},
        )
        return int(result.scalar_one())

    async def get_quote(self, quote_id: uuid.UUID, organization_id: uuid.UUID) -> Quote:
        result = await self.db.execute(
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.evidences))
            .where(Quote.id == quote_id, Quote.organization_id == organization_id)
            .execution_options(populate_existing=True)
        )
        quote = result.scalar_one_or_none()
        if quote is None:
            raise AppError("Cotação não encontrada.", status_code=404, code="NOT_FOUND")
        return quote

    def _ensure_draft(self, quote: Quote) -> None:
        if quote.status != QuoteStatus.DRAFT:
            raise AppError(
                "Somente cotações em rascunho podem ser alteradas.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )

    def _check_version(self, quote: Quote, expected_version: int) -> None:
        if quote.version != expected_version:
            raise AppError(
                "A cotação foi alterada por outro usuário. Atualize os dados e tente novamente.",
                status_code=409,
                code="QUOTE_VERSION_CONFLICT",
            )

    async def _validate_station(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError(
                "Os cadastros informados não pertencem à mesma organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        if not station.active:
            raise AppError("O posto informado está inativo.", status_code=400, code="VALIDATION_ERROR")
        return station

    async def _validate_distributor(self, distributor_id: uuid.UUID, organization_id: uuid.UUID) -> Distributor:
        distributor = await self.distributor_service.get_by_id(distributor_id, organization_id)
        if not distributor.active:
            raise AppError("A distribuidora informada está inativa.", status_code=400, code="VALIDATION_ERROR")
        return distributor

    async def _validate_base(
        self,
        *,
        distribution_base_id: uuid.UUID | None,
        distributor_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> None:
        if distribution_base_id is None:
            return
        base = await self.db.get(DistributionBase, distribution_base_id)
        if base is None or base.organization_id != organization_id:
            raise AppError(
                "A base informada não pertence à organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        if base.distributor_id != distributor_id:
            raise AppError(
                "A base informada não pertence à distribuidora.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

    async def _validate_product(self, product_id: uuid.UUID, organization_id: uuid.UUID) -> Product:
        product = await self.db.get(Product, product_id)
        if product is None or product.organization_id != organization_id:
            raise AppError(
                "O produto informado não pertence à organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        if not product.active or not product.purchasable:
            raise AppError(
                "Somente produtos ativos e compráveis podem ser adicionados.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        return product

    async def _validate_payment_term(self, payment_term_id: uuid.UUID, organization_id: uuid.UUID) -> PaymentTerm:
        term = await self.db.get(PaymentTerm, payment_term_id)
        if term is None or term.organization_id != organization_id:
            raise AppError(
                "A condição de pagamento não pertence à organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        if not term.active:
            raise AppError(
                "Somente condições de pagamento ativas podem ser usadas.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        return term

    def _validate_dates(self, quoted_at: datetime, valid_until: datetime) -> None:
        if valid_until <= quoted_at:
            raise AppError(
                "A validade deve ser posterior à data da cotação.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

    def _validate_item_amounts(self, data: dict[str, Any]) -> None:
        price = Decimal(str(data["quoted_price_per_liter"]))
        if price <= 0:
            raise AppError("O preço por litro deve ser maior que zero.", status_code=400, code="VALIDATION_ERROR")
        minimum = Decimal(str(data["minimum_volume_liters"]))
        if minimum <= 0:
            raise AppError("O volume mínimo deve ser maior que zero.", status_code=400, code="VALIDATION_ERROR")
        available = data.get("available_volume_liters")
        if available is not None and Decimal(str(available)) < 0:
            raise AppError("O volume disponível não pode ser negativo.", status_code=400, code="VALIDATION_ERROR")
        for field in ("discount_per_liter", "rebate_per_liter", "other_cost_per_liter"):
            if Decimal(str(data.get(field, "0"))) < 0:
                raise AppError("Valores financeiros não podem ser negativos.", status_code=400, code="VALIDATION_ERROR")
        other_cost = Decimal(str(data.get("other_cost_per_liter", "0")))
        if other_cost > 0 and not (data.get("other_cost_description") or "").strip():
            raise AppError(
                "Informe a descrição dos outros custos.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        freight_calc = data.get("freight_calculation_type", FreightCalculationType.NONE)
        if freight_calc == FreightCalculationType.TOTAL and data.get("freight_value_total") is None:
            raise AppError("Informe o frete total.", status_code=400, code="VALIDATION_ERROR")
        if freight_calc == FreightCalculationType.PER_LITER and data.get("freight_value_per_liter") is None:
            raise AppError("Informe o frete por litro.", status_code=400, code="VALIDATION_ERROR")

    def _item_fingerprint(self, item: QuoteItem) -> tuple:
        return (
            item.product_id,
            item.payment_term_id,
            str(item.quoted_price_per_liter),
            item.freight_type,
            str(item.freight_value_total or ""),
            str(item.freight_value_per_liter or ""),
            str(item.valid_until or ""),
        )

    def _check_duplicate_item(self, quote: Quote, candidate: QuoteItem, *, exclude_id: uuid.UUID | None = None) -> None:
        fingerprint = self._item_fingerprint(candidate)
        for item in quote.items:
            if exclude_id and item.id == exclude_id:
                continue
            if self._item_fingerprint(item) == fingerprint:
                raise AppError(
                    "Já existe uma condição idêntica para este produto.",
                    status_code=400,
                    code="DUPLICATE_QUOTE_ITEM",
                )

    async def list_quotes(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID] | None,
        station_id: uuid.UUID | None = None,
        distributor_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        status: str | None = None,
        source_channel: str | None = None,
        quoted_from: datetime | None = None,
        quoted_to: datetime | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        created_by: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "-quoted_at",
    ) -> tuple[list[Quote], int, dict[str, int]]:
        query = (
            select(Quote)
            .options(selectinload(Quote.items))
            .where(Quote.organization_id == organization_id)
        )
        if station_id:
            query = query.where(Quote.station_id == station_id)
        elif station_ids is not None:
            if not station_ids:
                return [], 0, {}
            query = query.where(Quote.station_id.in_(station_ids))
        if distributor_id:
            query = query.where(Quote.distributor_id == distributor_id)
        if status:
            query = query.where(Quote.status == status)
        if source_channel:
            query = query.where(Quote.source_channel == source_channel)
        if quoted_from:
            query = query.where(Quote.quoted_at >= quoted_from)
        if quoted_to:
            query = query.where(Quote.quoted_at <= quoted_to)
        if valid_from:
            query = query.where(Quote.valid_until >= valid_from)
        if valid_to:
            query = query.where(Quote.valid_until <= valid_to)
        if created_by:
            query = query.where(Quote.created_by == created_by)
        if product_id:
            query = query.join(QuoteItem, QuoteItem.quote_id == Quote.id).where(
                QuoteItem.product_id == product_id
            )
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Quote.seller_name.ilike(pattern),
                    Quote.external_reference.ilike(pattern),
                    Quote.notes.ilike(pattern),
                )
            )

        count_q = select(func.count()).select_from(query.distinct().subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        order_col = Quote.quoted_at.desc() if sort.startswith("-") else Quote.quoted_at.asc()
        query = query.distinct().order_by(order_col).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        quotes = list(result.scalars().unique().all())

        summary: dict[str, int] = {}
        summary_query = select(Quote.status, func.count()).where(Quote.organization_id == organization_id)
        if station_ids is not None:
            if station_ids:
                summary_query = summary_query.where(Quote.station_id.in_(station_ids))
            else:
                return quotes, total, summary
        if station_id:
            summary_query = summary_query.where(Quote.station_id == station_id)
        summary_query = summary_query.group_by(Quote.status)
        for row_status, count in (await self.db.execute(summary_query)).all():
            summary[row_status] = int(count)

        return quotes, total, summary

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        station = await self._validate_station(data["station_id"], organization_id)
        distributor = await self._validate_distributor(data["distributor_id"], organization_id)
        await self._validate_base(
            distribution_base_id=data.get("distribution_base_id"),
            distributor_id=distributor.id,
            organization_id=organization_id,
        )
        quoted_at = data["quoted_at"]
        valid_until = data["valid_until"]
        self._validate_dates(quoted_at, valid_until)

        quote = Quote(
            organization_id=organization_id,
            station_id=station.id,
            distributor_id=distributor.id,
            distribution_base_id=data.get("distribution_base_id"),
            quote_number=await self._next_quote_number(organization_id),
            quoted_at=quoted_at,
            valid_until=valid_until,
            source_channel=data["source_channel"],
            entry_method=data.get("entry_method", QuoteEntryMethod.MANUAL),
            seller_name=data.get("seller_name"),
            seller_contact=data.get("seller_contact"),
            external_reference=data.get("external_reference"),
            source_description=data.get("source_description"),
            notes=data.get("notes"),
            status=QuoteStatus.DRAFT,
            version=1,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(quote)
        await self.db.flush()

        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.CREATED,
            version=quote.version,
            user_id=user_id,
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote",
            entity_id=quote.id,
            action="create",
            after_data=self._serialize_quote(quote),
        )
        return quote

    async def update(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        quote = await self.get_quote(quote_id, organization_id)
        self._ensure_draft(quote)
        self._check_version(quote, expected_version)
        before = self._serialize_quote(quote)

        if "station_id" in data:
            await self._validate_station(data["station_id"], organization_id)
            quote.station_id = data["station_id"]
        if "distributor_id" in data:
            await self._validate_distributor(data["distributor_id"], organization_id)
            quote.distributor_id = data["distributor_id"]
        if "distribution_base_id" in data:
            await self._validate_base(
                distribution_base_id=data["distribution_base_id"],
                distributor_id=quote.distributor_id,
                organization_id=organization_id,
            )
            quote.distribution_base_id = data["distribution_base_id"]
        if "quoted_at" in data:
            quote.quoted_at = data["quoted_at"]
        if "valid_until" in data:
            quote.valid_until = data["valid_until"]
        if "quoted_at" in data or "valid_until" in data:
            self._validate_dates(quote.quoted_at, quote.valid_until)
        for field in (
            "source_channel",
            "entry_method",
            "seller_name",
            "seller_contact",
            "external_reference",
            "source_description",
            "notes",
        ):
            if field in data:
                setattr(quote, field, data[field])

        quote.version += 1
        quote.updated_by = user_id
        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.HEADER_UPDATED,
            version=quote.version,
            user_id=user_id,
            changed_fields={"before": before, "after": self._serialize_quote(quote)},
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote",
            entity_id=quote.id,
            action="update",
            before_data=before,
            after_data=self._serialize_quote(quote),
        )
        await self.db.flush()
        return quote

    async def add_item(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> QuoteItem:
        quote = await self.get_quote(quote_id, organization_id)
        self._ensure_draft(quote)
        self._check_version(quote, expected_version)
        self._validate_item_amounts(data)

        product = await self._validate_product(data["product_id"], organization_id)
        payment_term = await self._validate_payment_term(data["payment_term_id"], organization_id)
        await self._validate_base(
            distribution_base_id=data.get("distribution_base_id"),
            distributor_id=quote.distributor_id,
            organization_id=organization_id,
        )

        sequence = data.get("sequence") or (max((i.sequence for i in quote.items), default=0) + 1)
        item = QuoteItem(
            quote_id=quote.id,
            product_id=product.id,
            distribution_base_id=data.get("distribution_base_id") or quote.distribution_base_id,
            sequence=sequence,
            quoted_price_per_liter=Decimal(str(data["quoted_price_per_liter"])),
            payment_term_id=payment_term.id,
            payment_type_snapshot=payment_term.payment_type,
            payment_term_days_snapshot=payment_term.days,
            payment_term_name_snapshot=payment_term.name,
            freight_type=data.get("freight_type", FreightType.CIF),
            freight_calculation_type=data.get("freight_calculation_type", FreightCalculationType.NONE),
            freight_value_total=Decimal(str(data["freight_value_total"])) if data.get("freight_value_total") else None,
            freight_value_per_liter=Decimal(str(data["freight_value_per_liter"]))
            if data.get("freight_value_per_liter")
            else None,
            discount_per_liter=Decimal(str(data.get("discount_per_liter", "0"))),
            rebate_per_liter=Decimal(str(data.get("rebate_per_liter", "0"))),
            other_cost_per_liter=Decimal(str(data.get("other_cost_per_liter", "0"))),
            other_cost_description=data.get("other_cost_description"),
            minimum_volume_liters=Decimal(str(data["minimum_volume_liters"])),
            available_volume_liters=Decimal(str(data["available_volume_liters"]))
            if data.get("available_volume_liters") is not None
            else None,
            delivery_expected_at=data.get("delivery_expected_at"),
            valid_until=data.get("valid_until"),
            notes=data.get("notes"),
        )
        self._check_duplicate_item(quote, item)
        quote.items.append(item)
        quote.version += 1
        quote.updated_by = user_id
        await self.db.flush()

        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.ITEM_ADDED,
            version=quote.version,
            user_id=user_id,
            quote_item_id=item.id,
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote_item",
            entity_id=item.id,
            action="create",
            after_data={"quote_id": str(quote.id), "product_id": str(product.id)},
        )
        await self.db.flush()
        return item

    async def update_item(
        self,
        *,
        quote_id: uuid.UUID,
        item_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        data: dict[str, Any],
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> QuoteItem:
        quote = await self.get_quote(quote_id, organization_id)
        self._ensure_draft(quote)
        self._check_version(quote, expected_version)
        item = next((i for i in quote.items if i.id == item_id), None)
        if item is None:
            raise AppError("Item não encontrado.", status_code=404, code="NOT_FOUND")

        merged = {
            "quoted_price_per_liter": data.get("quoted_price_per_liter", item.quoted_price_per_liter),
            "minimum_volume_liters": data.get("minimum_volume_liters", item.minimum_volume_liters),
            "available_volume_liters": data.get("available_volume_liters", item.available_volume_liters),
            "discount_per_liter": data.get("discount_per_liter", item.discount_per_liter),
            "rebate_per_liter": data.get("rebate_per_liter", item.rebate_per_liter),
            "other_cost_per_liter": data.get("other_cost_per_liter", item.other_cost_per_liter),
            "other_cost_description": data.get("other_cost_description", item.other_cost_description),
            "freight_calculation_type": data.get("freight_calculation_type", item.freight_calculation_type),
            "freight_value_total": data.get("freight_value_total", item.freight_value_total),
            "freight_value_per_liter": data.get("freight_value_per_liter", item.freight_value_per_liter),
        }
        self._validate_item_amounts(merged)

        if "product_id" in data:
            await self._validate_product(data["product_id"], organization_id)
            item.product_id = data["product_id"]
        if "payment_term_id" in data:
            term = await self._validate_payment_term(data["payment_term_id"], organization_id)
            item.payment_term_id = term.id
            item.payment_type_snapshot = term.payment_type
            item.payment_term_days_snapshot = term.days
            item.payment_term_name_snapshot = term.name
        for field in (
            "quoted_price_per_liter",
            "freight_type",
            "freight_calculation_type",
            "freight_value_total",
            "freight_value_per_liter",
            "discount_per_liter",
            "rebate_per_liter",
            "other_cost_per_liter",
            "other_cost_description",
            "minimum_volume_liters",
            "available_volume_liters",
            "delivery_expected_at",
            "valid_until",
            "notes",
            "distribution_base_id",
            "sequence",
        ):
            if field in data:
                value = data[field]
                if field in {
                    "quoted_price_per_liter",
                    "freight_value_total",
                    "freight_value_per_liter",
                    "discount_per_liter",
                    "rebate_per_liter",
                    "other_cost_per_liter",
                    "minimum_volume_liters",
                    "available_volume_liters",
                } and value is not None:
                    value = Decimal(str(value))
                setattr(item, field, value)

        self._check_duplicate_item(quote, item, exclude_id=item.id)
        quote.version += 1
        quote.updated_by = user_id
        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.ITEM_UPDATED,
            version=quote.version,
            user_id=user_id,
            quote_item_id=item.id,
            request_id=request_id,
        )
        await self.audit.log(ctx=audit_ctx, entity_type="quote_item", entity_id=item.id, action="update")
        await self.db.flush()
        return item

    async def remove_item(
        self,
        *,
        quote_id: uuid.UUID,
        item_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> None:
        quote = await self.get_quote(quote_id, organization_id)
        self._ensure_draft(quote)
        self._check_version(quote, expected_version)
        item = next((i for i in quote.items if i.id == item_id), None)
        if item is None:
            raise AppError("Item não encontrado.", status_code=404, code="NOT_FOUND")
        quote.items.remove(item)
        quote.version += 1
        quote.updated_by = user_id
        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.ITEM_REMOVED,
            version=quote.version,
            user_id=user_id,
            quote_item_id=item_id,
            request_id=request_id,
        )
        await self.audit.log(ctx=audit_ctx, entity_type="quote_item", entity_id=item_id, action="delete")
        await self.db.delete(item)
        await self.db.flush()

    async def get_item_prefill(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        distributor_id: uuid.UUID,
        product_id: uuid.UUID,
        distribution_base_id: uuid.UUID | None = None,
        reference_date: date | None = None,
    ) -> dict[str, Any]:
        rule = await self.supplier_rule_service.resolve_effective_rule(
            organization_id=organization_id,
            station_id=station_id,
            distributor_id=distributor_id,
            product_id=product_id,
            distribution_base_id=distribution_base_id,
            reference_date=reference_date or date.today(),
        )
        return {
            "minimum_volume_liters": str(rule.minimum_volume_liters),
            "distribution_base_id": str(rule.distribution_base_id) if rule.distribution_base_id else None,
            "supplier_allowed": rule.allowed,
            "rule_source": rule.rule_source,
            "alert_supplier_not_allowed": not rule.allowed,
        }

    async def _validate_activation(self, quote: Quote) -> list[str]:
        warnings: list[str] = []
        now = datetime.now(UTC)
        if self._as_utc(quote.valid_until) <= now:
            raise AppError("Esta cotação já está vencida.", status_code=400, code="QUOTE_EXPIRED")
        if not quote.items:
            raise AppError("Adicione ao menos um item antes de ativar.", status_code=400, code="VALIDATION_ERROR")

        channel = QuoteSourceChannel(quote.source_channel)
        active_evidences = [e for e in quote.evidences if e.active and not e.is_supplemental]
        if channel in EVIDENCE_REQUIRED_CHANNELS and not active_evidences:
            raise AppError(
                "Adicione uma evidência antes de ativar esta cotação.",
                status_code=400,
                code="QUOTE_EVIDENCE_REQUIRED",
            )
        if channel == QuoteSourceChannel.PHONE:
            if not (quote.seller_name or "").strip() or not (quote.seller_contact or "").strip():
                raise AppError(
                    "Informe vendedor e contato para cotações por telefone.",
                    status_code=400,
                    code="VALIDATION_ERROR",
                )
            if not (quote.notes or "").strip():
                raise AppError(
                    "Descreva a confirmação verbal nas observações.",
                    status_code=400,
                    code="VALIDATION_ERROR",
                )
        if channel == QuoteSourceChannel.OTHER and not (quote.source_description or "").strip():
            raise AppError(
                "Informe a descrição da origem.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        for item in quote.items:
            if item.valid_until and self._as_utc(item.valid_until) <= now:
                raise AppError(
                    "Existem itens com validade vencida.",
                    status_code=400,
                    code="QUOTE_EXPIRED",
                )
            if item.available_volume_liters is not None and item.available_volume_liters < item.minimum_volume_liters:
                warnings.append(
                    f"Volume disponível inferior ao mínimo no produto {item.product_id}."
                )

        rule = await self.supplier_rule_service.resolve_effective_rule(
            organization_id=quote.organization_id,
            station_id=quote.station_id,
            distributor_id=quote.distributor_id,
            product_id=quote.items[0].product_id,
            distribution_base_id=quote.distribution_base_id,
            reference_date=quote.quoted_at.date(),
        )
        if not rule.allowed:
            warnings.append("A distribuidora não possui regra explícita de fornecimento para este posto.")
        return warnings

    async def activate(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        quote = await self.get_quote(quote_id, organization_id)
        if quote.status == QuoteStatus.ACTIVE:
            return quote
        self._ensure_draft(quote)
        self._check_version(quote, expected_version)
        await self._validate_station(quote.station_id, organization_id)
        await self._validate_distributor(quote.distributor_id, organization_id)
        warnings = await self._validate_activation(quote)

        if quote.replaces_quote_id:
            original = await self.get_quote(quote.replaces_quote_id, organization_id)
            if original.status == QuoteStatus.ACTIVE:
                original.status = QuoteStatus.SUPERSEDED
                original.superseded_at = datetime.now(UTC)
                original.superseded_by_quote_id = quote.id
                await self.history.record(
                    quote_id=original.id,
                    action=QuoteChangeAction.SUPERSEDED,
                    version=original.version,
                    user_id=user_id,
                    metadata={"superseded_by_quote_id": str(quote.id)},
                    request_id=request_id,
                )

        quote.status = QuoteStatus.ACTIVE
        quote.activated_at = datetime.now(UTC)
        quote.activated_by = user_id
        quote.version += 1
        quote.updated_by = user_id

        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.ACTIVATED,
            version=quote.version,
            user_id=user_id,
            metadata={"warnings": warnings} if warnings else None,
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote",
            entity_id=quote.id,
            action="activate",
            after_data=self._serialize_quote(quote),
        )
        await self.db.flush()
        return quote

    async def cancel(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        expected_version: int | None = None,
        audit_ctx: AuditContext | None = None,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        quote = await self.get_quote(quote_id, organization_id)
        if quote.status == QuoteStatus.CANCELLED:
            return quote
        if quote.status not in {QuoteStatus.DRAFT, QuoteStatus.ACTIVE}:
            raise AppError(
                "Esta cotação não pode ser cancelada.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )
        if expected_version is not None:
            self._check_version(quote, expected_version)
        if not reason.strip():
            raise AppError("Informe o motivo do cancelamento.", status_code=400, code="VALIDATION_ERROR")

        quote.status = QuoteStatus.CANCELLED
        quote.cancelled_at = datetime.now(UTC)
        quote.cancelled_by = user_id
        quote.cancellation_reason = reason.strip()
        quote.version += 1
        quote.updated_by = user_id

        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.CANCELLED,
            version=quote.version,
            user_id=user_id,
            reason=reason.strip(),
            request_id=request_id,
        )
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="quote",
                entity_id=quote.id,
                action="cancel",
                after_data={"reason": reason.strip()},
            )
        await self.db.flush()
        return quote

    async def revise(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        source = await self.get_quote(quote_id, organization_id)
        if source.status != QuoteStatus.ACTIVE:
            raise AppError(
                "Somente cotações ativas podem ser revisadas.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )
        if not reason.strip():
            raise AppError("Informe o motivo da revisão.", status_code=400, code="VALIDATION_ERROR")

        source_items = list(source.items)
        draft = Quote(
            organization_id=source.organization_id,
            station_id=source.station_id,
            distributor_id=source.distributor_id,
            distribution_base_id=source.distribution_base_id,
            quote_number=await self._next_quote_number(organization_id),
            quoted_at=source.quoted_at,
            valid_until=source.valid_until,
            source_channel=source.source_channel,
            entry_method=source.entry_method,
            seller_name=source.seller_name,
            seller_contact=source.seller_contact,
            external_reference=source.external_reference,
            source_description=source.source_description,
            notes=source.notes,
            status=QuoteStatus.DRAFT,
            version=1,
            replaces_quote_id=source.id,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(draft)
        await self.db.flush()

        for item in sorted(source_items, key=lambda i: i.sequence):
            clone = QuoteItem(
                quote_id=draft.id,
                product_id=item.product_id,
                distribution_base_id=item.distribution_base_id,
                sequence=item.sequence,
                quoted_price_per_liter=item.quoted_price_per_liter,
                payment_term_id=item.payment_term_id,
                payment_type_snapshot=item.payment_type_snapshot,
                payment_term_days_snapshot=item.payment_term_days_snapshot,
                payment_term_name_snapshot=item.payment_term_name_snapshot,
                freight_type=item.freight_type,
                freight_calculation_type=item.freight_calculation_type,
                freight_value_total=item.freight_value_total,
                freight_value_per_liter=item.freight_value_per_liter,
                discount_per_liter=item.discount_per_liter,
                rebate_per_liter=item.rebate_per_liter,
                other_cost_per_liter=item.other_cost_per_liter,
                other_cost_description=item.other_cost_description,
                minimum_volume_liters=item.minimum_volume_liters,
                available_volume_liters=item.available_volume_liters,
                delivery_expected_at=item.delivery_expected_at,
                valid_until=item.valid_until,
                notes=item.notes,
            )
            self.db.add(clone)

        await self.history.record(
            quote_id=source.id,
            action=QuoteChangeAction.REVISION_CREATED,
            version=source.version,
            user_id=user_id,
            reason=reason.strip(),
            metadata={"revision_quote_id": str(draft.id)},
            request_id=request_id,
        )
        await self.history.record(
            quote_id=draft.id,
            action=QuoteChangeAction.CREATED,
            version=draft.version,
            user_id=user_id,
            reason=reason.strip(),
            metadata={"replaces_quote_id": str(source.id)},
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote",
            entity_id=draft.id,
            action="revise",
            metadata={"source_quote_id": str(source.id), "reason": reason.strip()},
        )
        await self.db.flush()
        return draft

    async def duplicate(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        target_station_id: uuid.UUID,
        quoted_at: datetime,
        valid_until: datetime,
        copy_evidences: bool,
        notes: str | None = None,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> Quote:
        source = await self.get_quote(quote_id, organization_id)
        await self._validate_station(target_station_id, organization_id)
        self._validate_dates(quoted_at, valid_until)

        draft = Quote(
            organization_id=source.organization_id,
            station_id=target_station_id,
            distributor_id=source.distributor_id,
            distribution_base_id=source.distribution_base_id,
            quote_number=await self._next_quote_number(organization_id),
            quoted_at=quoted_at,
            valid_until=valid_until,
            source_channel=source.source_channel,
            entry_method=source.entry_method,
            seller_name=source.seller_name,
            seller_contact=source.seller_contact,
            external_reference=source.external_reference,
            source_description=source.source_description,
            notes=notes.strip() if notes and notes.strip() else source.notes,
            status=QuoteStatus.DRAFT,
            version=1,
            duplicated_from_quote_id=source.id,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(draft)
        await self.db.flush()

        copied_storage_keys: list[str] = []
        storage = get_object_storage()
        try:
            for item in sorted(source.items, key=lambda i: i.sequence):
                self.db.add(
                    QuoteItem(
                        quote_id=draft.id,
                        product_id=item.product_id,
                        distribution_base_id=item.distribution_base_id,
                        sequence=item.sequence,
                        quoted_price_per_liter=item.quoted_price_per_liter,
                        payment_term_id=item.payment_term_id,
                        payment_type_snapshot=item.payment_type_snapshot,
                        payment_term_days_snapshot=item.payment_term_days_snapshot,
                        payment_term_name_snapshot=item.payment_term_name_snapshot,
                        freight_type=item.freight_type,
                        freight_calculation_type=item.freight_calculation_type,
                        freight_value_total=item.freight_value_total,
                        freight_value_per_liter=item.freight_value_per_liter,
                        discount_per_liter=item.discount_per_liter,
                        rebate_per_liter=item.rebate_per_liter,
                        other_cost_per_liter=item.other_cost_per_liter,
                        other_cost_description=item.other_cost_description,
                        minimum_volume_liters=item.minimum_volume_liters,
                        available_volume_liters=item.available_volume_liters,
                        delivery_expected_at=item.delivery_expected_at,
                        valid_until=item.valid_until,
                        notes=item.notes,
                    )
                )

            if copy_evidences:
                for evidence in sorted(source.evidences, key=lambda e: e.uploaded_at):
                    if not evidence.active:
                        continue
                    stored_name = f"{uuid.uuid4().hex}{evidence.file_extension}"
                    storage_key = f"quotes/{draft.organization_id}/{draft.id}/{stored_name}"
                    storage.copy_object(
                        source_key=evidence.storage_key,
                        dest_key=storage_key,
                        content_type=evidence.content_type,
                    )
                    copied_storage_keys.append(storage_key)
                    clone = QuoteEvidence(
                        quote_id=draft.id,
                        category=evidence.category,
                        original_file_name=evidence.original_file_name,
                        stored_file_name=stored_name,
                        content_type=evidence.content_type,
                        file_extension=evidence.file_extension,
                        size_bytes=evidence.size_bytes,
                        sha256=evidence.sha256,
                        storage_key=storage_key,
                        is_supplemental=False,
                        active=True,
                        uploaded_by=user_id,
                        uploaded_at=datetime.now(UTC),
                        source_evidence_id=evidence.id,
                    )
                    self.db.add(clone)
                    await self.db.flush()
                    await self.history.record(
                        quote_id=draft.id,
                        action=QuoteChangeAction.EVIDENCE_ADDED,
                        version=draft.version,
                        user_id=user_id,
                        quote_evidence_id=clone.id,
                        metadata={
                            "file_name": evidence.original_file_name,
                            "sha256": evidence.sha256,
                            "copied_from": str(evidence.id),
                        },
                        request_id=request_id,
                    )

            await self.history.record(
                quote_id=draft.id,
                action=QuoteChangeAction.DUPLICATED,
                version=draft.version,
                user_id=user_id,
                metadata={"source_quote_id": str(source.id), "copy_evidences": copy_evidences},
                request_id=request_id,
            )
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="quote",
                entity_id=draft.id,
                action="duplicate",
                metadata={"source_quote_id": str(source.id), "copy_evidences": copy_evidences},
            )
            await self.db.flush()
            return draft
        except Exception:
            for key in copied_storage_keys:
                storage.delete_object(key=key)
            raise

    async def run_expiration(self, *, organization_id: uuid.UUID | None = None) -> dict[str, int | bool | str]:
        from app.services.quote_expiration_service import QuoteExpirationService

        return await QuoteExpirationService(self.db).run(
            organization_id=organization_id,
            origin="API",
        )

    async def find_similar_quotes(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        distributor_id: uuid.UUID,
        quoted_at: datetime,
    ) -> list[Quote]:
        window = timedelta(minutes=settings.quote_duplicate_warning_window_minutes)
        result = await self.db.execute(
            select(Quote)
            .where(
                Quote.organization_id == organization_id,
                Quote.station_id == station_id,
                Quote.distributor_id == distributor_id,
                Quote.quoted_at >= quoted_at - window,
                Quote.quoted_at <= quoted_at + window,
                Quote.status.in_([QuoteStatus.DRAFT, QuoteStatus.ACTIVE]),
            )
            .limit(5)
        )
        return list(result.scalars().all())

    def _serialize_quote(self, quote: Quote) -> dict[str, Any]:
        return {
            "id": str(quote.id),
            "quote_number": quote.quote_number,
            "station_id": str(quote.station_id),
            "distributor_id": str(quote.distributor_id),
            "status": quote.status,
            "version": quote.version,
            "quoted_at": quote.quoted_at.isoformat(),
            "valid_until": quote.valid_until.isoformat(),
        }
