import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.master_data_enums import PaymentType
from app.models.payment_term import PaymentTerm
from app.services.audit_service import AuditContext, AuditService
from app.utils.text import normalize_name


class PaymentTermService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_payment_terms(
        self,
        *,
        organization_id: uuid.UUID,
        payment_type: str | None = None,
        active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PaymentTerm], int]:
        query = select(PaymentTerm).where(PaymentTerm.organization_id == organization_id)
        if payment_type:
            query = query.where(PaymentTerm.payment_type == payment_type)
        if active is not None:
            query = query.where(PaymentTerm.active.is_(active))
        if search:
            term = f"%{search}%"
            query = query.where(
                or_(PaymentTerm.code.ilike(term), PaymentTerm.name.ilike(term))
            )

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(PaymentTerm.payment_type, PaymentTerm.days, PaymentTerm.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, term_id: uuid.UUID, organization_id: uuid.UUID) -> PaymentTerm:
        term = await self.db.get(PaymentTerm, term_id)
        if term is None or term.organization_id != organization_id:
            raise AppError("Condição de pagamento não encontrada.", status_code=404, code="NOT_FOUND")
        return term

    def _validate_payment_type_and_days(self, payment_type: str, days: int) -> None:
        try:
            ptype = PaymentType(payment_type)
        except ValueError as exc:
            raise AppError(
                "Tipo de pagamento inválido.",
                status_code=400,
                code="INVALID_PAYMENT_TERM",
            ) from exc

        if ptype == PaymentType.CASH and days != 0:
            raise AppError(
                "Condição à vista deve possuir zero dias.",
                status_code=400,
                code="INVALID_PAYMENT_TERM",
            )
        if ptype == PaymentType.TERM and days <= 0:
            raise AppError(
                "Condição a prazo deve possuir dias maiores que zero.",
                status_code=400,
                code="INVALID_PAYMENT_TERM",
            )
        if ptype == PaymentType.ANTICIPATED and days != 0:
            raise AppError(
                "Condição antecipada deve possuir zero dias nesta sprint.",
                status_code=400,
                code="INVALID_PAYMENT_TERM",
            )

    async def _ensure_code_unique(
        self, organization_id: uuid.UUID, code: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(PaymentTerm).where(
            PaymentTerm.organization_id == organization_id,
            PaymentTerm.code == code,
        )
        if exclude_id:
            query = query.where(PaymentTerm.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise AppError(
                "Já existe uma condição com este código.",
                status_code=409,
                code="VALIDATION_ERROR",
            )

    async def _ensure_combination_unique(
        self,
        organization_id: uuid.UUID,
        payment_type: str,
        days: int,
        normalized_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        query = select(PaymentTerm).where(
            PaymentTerm.organization_id == organization_id,
            PaymentTerm.payment_type == payment_type,
            PaymentTerm.days == days,
            PaymentTerm.normalized_name == normalized_name,
        )
        if exclude_id:
            query = query.where(PaymentTerm.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise AppError(
                "Já existe uma condição com esta combinação de tipo, dias e nome.",
                status_code=409,
                code="VALIDATION_ERROR",
            )

    async def create(
        self, *, organization_id: uuid.UUID, data: dict, audit_ctx: AuditContext
    ) -> PaymentTerm:
        code = str(data["code"]).strip().upper()
        name = str(data["name"]).strip()
        if not code or not name:
            raise AppError(
                "Código e nome são obrigatórios.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        payment_type = data["payment_type"]
        days = int(data["days"])
        self._validate_payment_type_and_days(payment_type, days)

        normalized = normalize_name(name)
        await self._ensure_code_unique(organization_id, code)
        await self._ensure_combination_unique(organization_id, payment_type, days, normalized)

        term = PaymentTerm(
            organization_id=organization_id,
            code=code,
            name=name,
            normalized_name=normalized,
            payment_type=payment_type,
            days=days,
            description=data.get("description"),
            active=data.get("active", True),
        )
        self.db.add(term)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="payment_term",
            entity_id=term.id,
            action="create",
            after_data=self._serialize(term),
        )
        return term

    async def update(
        self, *, term: PaymentTerm, data: dict, audit_ctx: AuditContext
    ) -> PaymentTerm:
        before = self._serialize(term)

        payment_type = data.get("payment_type", term.payment_type)
        days = int(data["days"]) if "days" in data else term.days
        if "payment_type" in data or "days" in data:
            self._validate_payment_type_and_days(payment_type, days)
            term.payment_type = payment_type
            term.days = days

        if "code" in data:
            code = str(data["code"]).strip().upper()
            if not code:
                raise AppError("Código é obrigatório.", status_code=400, code="VALIDATION_ERROR")
            await self._ensure_code_unique(term.organization_id, code, exclude_id=term.id)
            term.code = code

        if "name" in data:
            name = str(data["name"]).strip()
            if not name:
                raise AppError("Nome é obrigatório.", status_code=400, code="VALIDATION_ERROR")
            term.name = name
            term.normalized_name = normalize_name(name)

        if "name" in data or "payment_type" in data or "days" in data:
            await self._ensure_combination_unique(
                term.organization_id,
                term.payment_type,
                term.days,
                term.normalized_name,
                exclude_id=term.id,
            )

        if "description" in data:
            term.description = data["description"]
        if "active" in data:
            term.active = data["active"]

        term.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="payment_term",
            entity_id=term.id,
            action="update",
            before_data=before,
            after_data=self._serialize(term),
        )
        return term

    async def deactivate(
        self, *, term: PaymentTerm, reason: str, audit_ctx: AuditContext
    ) -> PaymentTerm:
        before = self._serialize(term)
        term.active = False
        term.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="payment_term",
            entity_id=term.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(term),
            metadata={"reason": reason},
        )
        return term

    async def reactivate(self, *, term: PaymentTerm, audit_ctx: AuditContext) -> PaymentTerm:
        before = self._serialize(term)
        term.active = True
        term.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="payment_term",
            entity_id=term.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(term),
        )
        return term

    def _serialize(self, term: PaymentTerm) -> dict:
        return {
            "id": str(term.id),
            "organization_id": str(term.organization_id),
            "code": term.code,
            "name": term.name,
            "normalized_name": term.normalized_name,
            "payment_type": term.payment_type,
            "days": term.days,
            "description": term.description,
            "active": term.active,
        }
