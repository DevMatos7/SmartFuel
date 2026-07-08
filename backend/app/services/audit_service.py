import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.utils.sanitize import sanitize_for_audit


@dataclass
class AuditContext:
    organization_id: uuid.UUID | None
    user_id: uuid.UUID | None
    ip_address: str | None
    request_id: str | None


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        ctx: AuditContext,
        entity_type: str,
        entity_id: uuid.UUID | None,
        action: str,
        before_data: dict | None = None,
        after_data: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_data=sanitize_for_audit(before_data),
            after_data=sanitize_for_audit(after_data),
            metadata_=metadata,
            ip_address=ctx.ip_address,
            request_id=ctx.request_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_logs(
        self,
        *,
        organization_id: uuid.UUID,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if date_from:
            query = query.where(AuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AuditLog.created_at <= date_to)

        count_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = int(count_result.scalar_one())

        query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
