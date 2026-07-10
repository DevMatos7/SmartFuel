from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.quote_comparison_enums import DEFAULT_DAY_COUNT_BASIS, FINANCIAL_METHODOLOGY_VERSION
from app.models.financial_parameter import FinancialParameter
from app.services.audit_service import AuditContext, AuditService


class FinancialParameterService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    def _serialize(self, row: FinancialParameter) -> dict:
        return {
            "id": str(row.id),
            "annual_effective_rate": str(row.annual_effective_rate),
            "day_count_basis": row.day_count_basis,
            "methodology_version": row.methodology_version,
            "valid_from": row.valid_from.isoformat(),
            "valid_until": row.valid_until.isoformat() if row.valid_until else None,
            "active": row.active,
            "notes": row.notes,
        }

    async def _ensure_no_overlap(
        self,
        *,
        organization_id: uuid.UUID,
        valid_from: datetime,
        valid_until: datetime | None,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(FinancialParameter).where(
            FinancialParameter.organization_id == organization_id,
            FinancialParameter.active.is_(True),
        )
        if exclude_id:
            query = query.where(FinancialParameter.id != exclude_id)
        result = await self.db.execute(query)
        for row in result.scalars().all():
            row_end = row.valid_until
            new_end = valid_until
            if row.valid_from <= (new_end or datetime.max.replace(tzinfo=UTC)):
                if valid_from <= (row_end or datetime.max.replace(tzinfo=UTC)):
                    raise AppError(
                        "Já existe um parâmetro financeiro vigente no período informado.",
                        status_code=409,
                        code="FINANCIAL_PARAMETER_OVERLAP",
                    )

    async def list_parameters(
        self,
        *,
        organization_id: uuid.UUID,
        active: bool | None = None,
        valid_on: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FinancialParameter], int]:
        query = select(FinancialParameter).where(FinancialParameter.organization_id == organization_id)
        if active is not None:
            query = query.where(FinancialParameter.active.is_(active))
        if valid_on is not None:
            ref = valid_on if valid_on.tzinfo else valid_on.replace(tzinfo=UTC)
            query = query.where(
                FinancialParameter.valid_from <= ref,
                or_(FinancialParameter.valid_until.is_(None), FinancialParameter.valid_until > ref),
            )
        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())
        query = (
            query.order_by(FinancialParameter.valid_from.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(query)).scalars().all()
        return list(rows), total

    async def get_by_id(self, parameter_id: uuid.UUID, organization_id: uuid.UUID) -> FinancialParameter:
        row = await self.db.get(FinancialParameter, parameter_id)
        if row is None or row.organization_id != organization_id:
            raise AppError("Parâmetro financeiro não encontrado.", status_code=404, code="NOT_FOUND")
        return row

    async def find_effective(
        self,
        *,
        organization_id: uuid.UUID,
        reference_datetime: datetime,
        historical: bool = True,
    ) -> FinancialParameter | None:
        ref = reference_datetime if reference_datetime.tzinfo else reference_datetime.replace(tzinfo=UTC)
        query = (
            select(FinancialParameter)
            .where(
                FinancialParameter.organization_id == organization_id,
                FinancialParameter.valid_from <= ref,
                or_(FinancialParameter.valid_until.is_(None), FinancialParameter.valid_until > ref),
            )
            .order_by(FinancialParameter.valid_from.desc())
            .limit(1)
        )
        if not historical:
            query = query.where(FinancialParameter.active.is_(True))
        return (await self.db.execute(query)).scalar_one_or_none()

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        annual_effective_rate: Decimal,
        day_count_basis: int,
        valid_from: datetime,
        valid_until: datetime | None,
        notes: str | None,
        actor_id: uuid.UUID,
        audit: AuditContext,
    ) -> FinancialParameter:
        if annual_effective_rate < 0:
            raise AppError("A taxa anual deve ser maior ou igual a zero.", status_code=400, code="INVALID_RATE")
        if day_count_basis <= 0:
            raise AppError("A base de dias deve ser maior que zero.", status_code=400, code="INVALID_DAY_BASIS")
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"financial_parameter:{organization_id}"},
        )
        await self._ensure_no_overlap(
            organization_id=organization_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        row = FinancialParameter(
            organization_id=organization_id,
            annual_effective_rate=annual_effective_rate,
            day_count_basis=day_count_basis or DEFAULT_DAY_COUNT_BASIS,
            methodology_version=FINANCIAL_METHODOLOGY_VERSION,
            valid_from=valid_from,
            valid_until=valid_until,
            notes=notes,
            active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self.audit.log(
            ctx=audit,
            entity_type="financial_parameter",
            entity_id=row.id,
            action="create",
            after_data=self._serialize(row),
        )
        return row

    async def close_validity(
        self,
        *,
        parameter_id: uuid.UUID,
        organization_id: uuid.UUID,
        valid_until: datetime,
        reason: str | None,
        actor_id: uuid.UUID,
        audit: AuditContext,
    ) -> FinancialParameter:
        row = await self.get_by_id(parameter_id, organization_id)
        if row.valid_until is not None and row.valid_until <= valid_until:
            return row
        before = self._serialize(row)
        row.valid_until = valid_until
        row.updated_by = actor_id
        await self.db.flush()
        await self.audit.log(
            ctx=audit,
            entity_type="financial_parameter",
            entity_id=row.id,
            action="close_validity",
            before_data=before,
            after_data=self._serialize(row),
            metadata={"reason": reason},
        )
        return row

    async def deactivate(
        self,
        *,
        parameter_id: uuid.UUID,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        audit: AuditContext,
    ) -> FinancialParameter:
        row = await self.get_by_id(parameter_id, organization_id)
        before = self._serialize(row)
        row.active = False
        row.updated_by = actor_id
        await self.db.flush()
        await self.audit.log(
            ctx=audit,
            entity_type="financial_parameter",
            entity_id=row.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(row),
        )
        return row
