import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.master_data_enums import RuleSource
from app.models.distribution_base import DistributionBase
from app.models.distributor import Distributor
from app.models.product import Product
from app.models.station import Station
from app.models.station_supplier_rule import StationSupplierRule
from app.services.audit_service import AuditContext, AuditService
from app.services.distribution_base_service import DistributionBaseService
from app.services.distributor_service import DistributorService
from app.services.organization_business_settings_service import OrganizationBusinessSettingsService
from app.services.product_service import ProductService


@dataclass
class EffectiveRuleResult:
    allowed: bool
    minimum_volume_liters: Decimal
    rule_source: str
    rule_id: uuid.UUID | None
    distribution_base_id: uuid.UUID | None
    valid_from: date | None
    valid_until: date | None
    reason: str | None


class SupplierRuleService:
    DEFAULT_MINIMUM = Decimal("5000.000")

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.distributor_service = DistributorService(db)
        self.product_service = ProductService(db)
        self.base_service = DistributionBaseService(db)
        self.org_settings_service = OrganizationBusinessSettingsService(db)

    async def list_rules(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID | None = None,
        distributor_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        allowed: bool | None = None,
        valid_on: date | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StationSupplierRule], int]:
        query = select(StationSupplierRule).where(
            StationSupplierRule.organization_id == organization_id
        )
        if station_id:
            query = query.where(StationSupplierRule.station_id == station_id)
        if distributor_id:
            query = query.where(StationSupplierRule.distributor_id == distributor_id)
        if product_id:
            query = query.where(StationSupplierRule.product_id == product_id)
        if allowed is not None:
            query = query.where(StationSupplierRule.allowed.is_(allowed))
        if active is not None:
            query = query.where(StationSupplierRule.active.is_(active))
        if valid_on:
            query = query.where(
                StationSupplierRule.valid_from <= valid_on,
                or_(
                    StationSupplierRule.valid_until.is_(None),
                    StationSupplierRule.valid_until >= valid_on,
                ),
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(
                StationSupplierRule.station_id,
                StationSupplierRule.distributor_id,
                StationSupplierRule.priority,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, rule_id: uuid.UUID, organization_id: uuid.UUID) -> StationSupplierRule:
        rule = await self.db.get(StationSupplierRule, rule_id)
        if rule is None or rule.organization_id != organization_id:
            raise AppError("Regra de fornecimento não encontrada.", status_code=404, code="NOT_FOUND")
        return rule

    async def _ensure_station(self, station_id: uuid.UUID, organization_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != organization_id:
            raise AppError(
                "Os cadastros informados não pertencem à mesma organização.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        return station

    async def _ensure_distributor(
        self, distributor_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Distributor:
        return await self.distributor_service.get_by_id(distributor_id, organization_id)

    async def _ensure_product(
        self, product_id: uuid.UUID | None, organization_id: uuid.UUID
    ) -> Product | None:
        if product_id is None:
            return None
        return await self.product_service.get_by_id(product_id, organization_id)

    async def _ensure_base(
        self,
        base_id: uuid.UUID | None,
        distributor_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> DistributionBase | None:
        if base_id is None:
            return None
        base = await self.base_service.get_by_id(base_id, organization_id)
        if base.distributor_id != distributor_id:
            raise AppError(
                "A base informada não pertence à distribuidora.",
                status_code=400,
                code="CROSS_ORGANIZATION_REFERENCE",
            )
        return base

    def _validate_validity(self, valid_from: date, valid_until: date | None) -> None:
        if valid_until is not None and valid_until < valid_from:
            raise AppError(
                "A data final não pode ser anterior à data inicial.",
                status_code=400,
                code="INVALID_VALIDITY_PERIOD",
            )

    def _validate_minimum_volume(self, volume: Decimal) -> Decimal:
        if volume <= 0:
            raise AppError(
                "O volume mínimo deve ser maior que zero.",
                status_code=400,
                code="INVALID_MINIMUM_VOLUME",
            )
        return volume

    def _periods_overlap(
        self,
        a_from: date,
        a_until: date | None,
        b_from: date,
        b_until: date | None,
    ) -> bool:
        a_end = a_until or date.max
        b_end = b_until or date.max
        return a_from <= b_end and b_from <= a_end

    async def _ensure_no_overlap(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        distributor_id: uuid.UUID,
        product_id: uuid.UUID | None,
        valid_from: date,
        valid_until: date | None,
        priority: int,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(StationSupplierRule).where(
            StationSupplierRule.organization_id == organization_id,
            StationSupplierRule.station_id == station_id,
            StationSupplierRule.distributor_id == distributor_id,
            StationSupplierRule.active.is_(True),
            StationSupplierRule.priority == priority,
        )
        if product_id is None:
            query = query.where(StationSupplierRule.product_id.is_(None))
        else:
            query = query.where(StationSupplierRule.product_id == product_id)
        if exclude_id:
            query = query.where(StationSupplierRule.id != exclude_id)

        result = await self.db.execute(query)
        for existing in result.scalars().all():
            if self._periods_overlap(
                valid_from, valid_until, existing.valid_from, existing.valid_until
            ):
                raise AppError(
                    "Já existe uma regra vigente para este posto, distribuidora e produto no período informado.",
                    status_code=409,
                    code="SUPPLIER_RULE_OVERLAP",
                )

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        data: dict,
        created_by: uuid.UUID,
        audit_ctx: AuditContext,
    ) -> StationSupplierRule:
        station = await self._ensure_station(data["station_id"], organization_id)
        distributor = await self._ensure_distributor(data["distributor_id"], organization_id)
        product = await self._ensure_product(data.get("product_id"), organization_id)
        base = await self._ensure_base(
            data.get("distribution_base_id"), distributor.id, organization_id
        )

        valid_from = data["valid_from"]
        valid_until = data.get("valid_until")
        self._validate_validity(valid_from, valid_until)

        minimum = self._validate_minimum_volume(
            Decimal(str(data.get("minimum_volume_liters", settings.default_minimum_volume_liters)))
        )
        priority = int(data.get("priority", 100))

        await self._ensure_no_overlap(
            organization_id=organization_id,
            station_id=station.id,
            distributor_id=distributor.id,
            product_id=product.id if product else None,
            valid_from=valid_from,
            valid_until=valid_until,
            priority=priority,
        )

        rule = StationSupplierRule(
            organization_id=organization_id,
            station_id=station.id,
            distributor_id=distributor.id,
            product_id=product.id if product else None,
            distribution_base_id=base.id if base else None,
            allowed=data.get("allowed", True),
            minimum_volume_liters=minimum,
            valid_from=valid_from,
            valid_until=valid_until,
            contract_reference=data.get("contract_reference"),
            reason=data.get("reason"),
            notes=data.get("notes"),
            priority=priority,
            active=data.get("active", True),
            created_by=created_by,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station_supplier_rule",
            entity_id=rule.id,
            action="create",
            after_data=self._serialize(rule),
        )
        return rule

    async def update(
        self, *, rule: StationSupplierRule, data: dict, audit_ctx: AuditContext
    ) -> StationSupplierRule:
        before = self._serialize(rule)

        station_id = data.get("station_id", rule.station_id)
        distributor_id = data.get("distributor_id", rule.distributor_id)
        product_id = data.get("product_id", rule.product_id)
        base_id = data.get("distribution_base_id", rule.distribution_base_id)

        await self._ensure_station(station_id, rule.organization_id)
        await self._ensure_distributor(distributor_id, rule.organization_id)
        await self._ensure_product(product_id, rule.organization_id)
        await self._ensure_base(base_id, distributor_id, rule.organization_id)

        valid_from = data.get("valid_from", rule.valid_from)
        valid_until = data.get("valid_until", rule.valid_until)
        self._validate_validity(valid_from, valid_until)

        priority = int(data.get("priority", rule.priority))

        if any(
            k in data
            for k in (
                "station_id",
                "distributor_id",
                "product_id",
                "valid_from",
                "valid_until",
                "priority",
            )
        ):
            await self._ensure_no_overlap(
                organization_id=rule.organization_id,
                station_id=station_id,
                distributor_id=distributor_id,
                product_id=product_id,
                valid_from=valid_from,
                valid_until=valid_until,
                priority=priority,
                exclude_id=rule.id,
            )

        rule.station_id = station_id
        rule.distributor_id = distributor_id
        rule.product_id = product_id
        rule.distribution_base_id = base_id
        rule.valid_from = valid_from
        rule.valid_until = valid_until
        rule.priority = priority

        if "allowed" in data:
            rule.allowed = data["allowed"]
        if "minimum_volume_liters" in data:
            rule.minimum_volume_liters = self._validate_minimum_volume(
                Decimal(str(data["minimum_volume_liters"]))
            )
        for field in ("contract_reference", "reason", "notes", "active"):
            if field in data:
                setattr(rule, field, data[field])

        rule.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station_supplier_rule",
            entity_id=rule.id,
            action="update",
            before_data=before,
            after_data=self._serialize(rule),
        )
        return rule

    async def deactivate(
        self, *, rule: StationSupplierRule, reason: str, audit_ctx: AuditContext
    ) -> StationSupplierRule:
        before = self._serialize(rule)
        rule.active = False
        rule.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station_supplier_rule",
            entity_id=rule.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(rule),
            metadata={"reason": reason},
        )
        return rule

    async def reactivate(
        self, *, rule: StationSupplierRule, audit_ctx: AuditContext
    ) -> StationSupplierRule:
        await self._ensure_no_overlap(
            organization_id=rule.organization_id,
            station_id=rule.station_id,
            distributor_id=rule.distributor_id,
            product_id=rule.product_id,
            valid_from=rule.valid_from,
            valid_until=rule.valid_until,
            priority=rule.priority,
            exclude_id=rule.id,
        )
        before = self._serialize(rule)
        rule.active = True
        rule.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station_supplier_rule",
            entity_id=rule.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(rule),
        )
        return rule

    async def close_validity(
        self,
        *,
        rule: StationSupplierRule,
        valid_until: date,
        reason: str | None,
        audit_ctx: AuditContext,
    ) -> StationSupplierRule:
        self._validate_validity(rule.valid_from, valid_until)
        before = self._serialize(rule)
        rule.valid_until = valid_until
        rule.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="station_supplier_rule",
            entity_id=rule.id,
            action="close_validity",
            before_data=before,
            after_data=self._serialize(rule),
            metadata={"reason": reason},
        )
        return rule

    def _is_valid_on(self, rule: StationSupplierRule, reference_date: date) -> bool:
        if not rule.active:
            return False
        if rule.valid_from > reference_date:
            return False
        return rule.valid_until is None or rule.valid_until >= reference_date

    async def _find_best_rule(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        distributor_id: uuid.UUID,
        product_id: uuid.UUID,
        reference_date: date,
        specific: bool,
        distribution_base_id: uuid.UUID | None = None,
    ) -> StationSupplierRule | None:
        base_candidates: list[uuid.UUID | None]
        if distribution_base_id is not None:
            base_candidates = [distribution_base_id, None]
        else:
            base_candidates = [None]

        for base_id in base_candidates:
            query = select(StationSupplierRule).where(
                StationSupplierRule.organization_id == organization_id,
                StationSupplierRule.station_id == station_id,
                StationSupplierRule.distributor_id == distributor_id,
                StationSupplierRule.active.is_(True),
                StationSupplierRule.valid_from <= reference_date,
                or_(
                    StationSupplierRule.valid_until.is_(None),
                    StationSupplierRule.valid_until >= reference_date,
                ),
            )
            if specific:
                query = query.where(StationSupplierRule.product_id == product_id)
            else:
                query = query.where(StationSupplierRule.product_id.is_(None))

            if base_id is None:
                query = query.where(StationSupplierRule.distribution_base_id.is_(None))
            else:
                query = query.where(StationSupplierRule.distribution_base_id == base_id)

            query = query.order_by(
                StationSupplierRule.priority.asc(),
                StationSupplierRule.valid_from.desc(),
            )
            result = await self.db.execute(query)
            rule = result.scalars().first()
            if rule:
                return rule
        return None

    def _rule_to_result(self, rule: StationSupplierRule, rule_source: str) -> EffectiveRuleResult:
        return EffectiveRuleResult(
            allowed=rule.allowed,
            minimum_volume_liters=rule.minimum_volume_liters,
            rule_source=rule_source,
            rule_id=rule.id,
            distribution_base_id=rule.distribution_base_id,
            valid_from=rule.valid_from,
            valid_until=rule.valid_until,
            reason=rule.reason,
        )

    async def resolve_effective_rule(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        distributor_id: uuid.UUID,
        product_id: uuid.UUID,
        reference_date: date | None = None,
        distribution_base_id: uuid.UUID | None = None,
    ) -> EffectiveRuleResult:
        await self._ensure_station(station_id, organization_id)
        await self._ensure_distributor(distributor_id, organization_id)
        await self._ensure_product(product_id, organization_id)
        if distribution_base_id is not None:
            base = await self.base_service.get_by_id(distribution_base_id, organization_id)
            if base.distributor_id != distributor_id:
                raise AppError(
                    "A base informada não pertence à distribuidora.",
                    status_code=400,
                    code="CROSS_ORGANIZATION_REFERENCE",
                )

        ref = reference_date or date.today()
        org_settings = await self.org_settings_service.get_for_organization(organization_id)
        default_minimum = org_settings.default_minimum_volume_liters

        specific = await self._find_best_rule(
            organization_id=organization_id,
            station_id=station_id,
            distributor_id=distributor_id,
            product_id=product_id,
            reference_date=ref,
            specific=True,
            distribution_base_id=distribution_base_id,
        )
        if specific:
            return self._rule_to_result(specific, RuleSource.PRODUCT_SPECIFIC)

        general = await self._find_best_rule(
            organization_id=organization_id,
            station_id=station_id,
            distributor_id=distributor_id,
            product_id=product_id,
            reference_date=ref,
            specific=False,
            distribution_base_id=distribution_base_id,
        )
        if general:
            return self._rule_to_result(general, RuleSource.DISTRIBUTOR_GENERAL)

        if org_settings.default_supplier_allowed:
            return EffectiveRuleResult(
                allowed=True,
                minimum_volume_liters=default_minimum,
                rule_source=RuleSource.ORGANIZATION_DEFAULT,
                rule_id=None,
                distribution_base_id=None,
                valid_from=None,
                valid_until=None,
                reason=None,
            )

        return EffectiveRuleResult(
            allowed=False,
            minimum_volume_liters=default_minimum,
            rule_source=RuleSource.NO_RULE,
            rule_id=None,
            distribution_base_id=None,
            valid_from=None,
            valid_until=None,
            reason=None,
        )

    def _serialize(self, rule: StationSupplierRule) -> dict:
        return {
            "id": str(rule.id),
            "organization_id": str(rule.organization_id),
            "station_id": str(rule.station_id),
            "distributor_id": str(rule.distributor_id),
            "product_id": str(rule.product_id) if rule.product_id else None,
            "distribution_base_id": (
                str(rule.distribution_base_id) if rule.distribution_base_id else None
            ),
            "allowed": rule.allowed,
            "minimum_volume_liters": str(rule.minimum_volume_liters),
            "valid_from": rule.valid_from.isoformat(),
            "valid_until": rule.valid_until.isoformat() if rule.valid_until else None,
            "contract_reference": rule.contract_reference,
            "reason": rule.reason,
            "notes": rule.notes,
            "priority": rule.priority,
            "active": rule.active,
            "created_by": str(rule.created_by),
        }
