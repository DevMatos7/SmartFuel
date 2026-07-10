from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.quote_enums import (
    ALLOWED_EVIDENCE_EXTENSIONS,
    ALLOWED_EVIDENCE_MIME_TYPES,
    EVIDENCE_REQUIRED_CHANNELS,
    QuoteChangeAction,
    QuoteSourceChannel,
    QuoteStatus,
)
from app.models.quote import Quote
from app.models.quote_evidence import QuoteEvidence
from app.services.audit_service import AuditContext, AuditService
from app.services.quote_history_service import QuoteHistoryService
from app.storage.object_storage import get_object_storage


class QuoteEvidenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.history = QuoteHistoryService(db)
        self.storage = get_object_storage()

    async def _get_quote(self, quote_id: uuid.UUID, organization_id: uuid.UUID) -> Quote:
        result = await self.db.execute(
            select(Quote)
            .options(selectinload(Quote.evidences))
            .where(Quote.id == quote_id, Quote.organization_id == organization_id)
            .execution_options(populate_existing=True)
        )
        quote = result.scalar_one_or_none()
        if quote is None:
            raise AppError("Cotação não encontrada.", status_code=404, code="NOT_FOUND")
        return quote

    def _validate_file(self, *, file_name: str, content_type: str, content: bytes) -> None:
        suffix = Path(file_name).suffix.lower()
        if suffix not in ALLOWED_EVIDENCE_EXTENSIONS:
            raise AppError(
                "O arquivo enviado não é permitido.",
                status_code=400,
                code="INVALID_EVIDENCE_FILE",
            )
        if content_type not in ALLOWED_EVIDENCE_MIME_TYPES:
            raise AppError(
                "O arquivo enviado não é permitido.",
                status_code=400,
                code="INVALID_EVIDENCE_FILE",
            )
        if len(content) == 0:
            raise AppError(
                "O arquivo está vazio.",
                status_code=400,
                code="INVALID_EVIDENCE_FILE",
            )
        if len(content) > settings.quote_evidence_max_bytes:
            raise AppError(
                "O arquivo excede o tamanho máximo permitido.",
                status_code=400,
                code="INVALID_EVIDENCE_FILE",
            )

    async def upload(
        self,
        *,
        quote_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        file_name: str,
        content_type: str,
        content: bytes,
        category: str,
        is_supplemental: bool,
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> QuoteEvidence:
        quote = await self._get_quote(quote_id, organization_id)
        if quote.status == QuoteStatus.DRAFT:
            pass
        elif quote.status in {QuoteStatus.ACTIVE, QuoteStatus.EXPIRED} and is_supplemental:
            pass
        else:
            raise AppError(
                "Somente rascunhos ou cotações ativas/expiradas com evidência suplementar permitem upload.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )

        if quote.version != expected_version:
            raise AppError(
                "A cotação foi alterada por outro usuário. Atualize os dados e tente novamente.",
                status_code=409,
                code="QUOTE_VERSION_CONFLICT",
            )

        self._validate_file(file_name=file_name, content_type=content_type, content=content)
        sha256 = hashlib.sha256(content).hexdigest()

        for evidence in quote.evidences:
            if evidence.sha256 == sha256 and evidence.active:
                raise AppError(
                    "Este arquivo já está anexado à cotação.",
                    status_code=400,
                    code="DUPLICATE_EVIDENCE",
                )

        stored_name = f"{uuid.uuid4().hex}{Path(file_name).suffix.lower()}"
        storage_key = f"quotes/{quote.organization_id}/{quote.id}/{stored_name}"
        self.storage.put_object(key=storage_key, data=content, content_type=content_type)

        evidence = QuoteEvidence(
            quote_id=quote.id,
            category=category,
            original_file_name=file_name,
            stored_file_name=stored_name,
            content_type=content_type,
            file_extension=Path(file_name).suffix.lower(),
            size_bytes=len(content),
            sha256=sha256,
            storage_key=storage_key,
            is_supplemental=is_supplemental,
            active=True,
            uploaded_by=user_id,
            uploaded_at=datetime.now(UTC),
        )
        try:
            self.db.add(evidence)
            quote.version += 1
            quote.updated_by = user_id

            action = (
                QuoteChangeAction.SUPPLEMENTAL_EVIDENCE_ADDED
                if is_supplemental
                else QuoteChangeAction.EVIDENCE_ADDED
            )
            await self.history.record(
                quote_id=quote.id,
                action=action,
                version=quote.version,
                user_id=user_id,
                quote_evidence_id=evidence.id,
                metadata={"file_name": file_name, "sha256": sha256},
                request_id=request_id,
            )
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="quote_evidence",
                entity_id=evidence.id,
                action="create",
                after_data={"quote_id": str(quote.id), "file_name": file_name, "sha256": sha256},
            )
            await self.db.flush()
            return evidence
        except Exception:
            self.storage.delete_object(key=storage_key)
            raise

    async def get_download(
        self,
        *,
        quote_id: uuid.UUID,
        evidence_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> tuple[bytes, str, str]:
        result = await self.db.execute(
            select(QuoteEvidence)
            .join(Quote, Quote.id == QuoteEvidence.quote_id)
            .where(
                QuoteEvidence.id == evidence_id,
                QuoteEvidence.quote_id == quote_id,
                Quote.organization_id == organization_id,
                QuoteEvidence.active.is_(True),
            )
        )
        evidence = result.scalar_one_or_none()
        if evidence is None:
            raise AppError("Evidência não encontrada.", status_code=404, code="NOT_FOUND")

        stream, _, _ = self.storage.get_object(key=evidence.storage_key)
        return stream.read(), evidence.content_type, evidence.original_file_name

    async def remove_from_draft(
        self,
        *,
        quote_id: uuid.UUID,
        evidence_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> None:
        quote = await self._get_quote(quote_id, organization_id)
        if quote.status != QuoteStatus.DRAFT:
            raise AppError(
                "Somente cotações em rascunho podem remover evidências.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )
        if quote.version != expected_version:
            raise AppError(
                "A cotação foi alterada por outro usuário. Atualize os dados e tente novamente.",
                status_code=409,
                code="QUOTE_VERSION_CONFLICT",
            )

        evidence = next((e for e in quote.evidences if e.id == evidence_id), None)
        if evidence is None:
            raise AppError("Evidência não encontrada.", status_code=404, code="NOT_FOUND")

        quote.evidences.remove(evidence)
        quote.version += 1
        quote.updated_by = user_id
        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.EVIDENCE_REMOVED,
            version=quote.version,
            user_id=user_id,
            quote_evidence_id=evidence_id,
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote_evidence",
            entity_id=evidence_id,
            action="delete",
            before_data={"quote_id": str(quote.id)},
        )
        await self.db.delete(evidence)
        await self.db.flush()

    async def deactivate(
        self,
        *,
        quote_id: uuid.UUID,
        evidence_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        audit_ctx: AuditContext,
        request_id: uuid.UUID | None = None,
    ) -> QuoteEvidence:
        quote = await self._get_quote(quote_id, organization_id)
        if quote.status != QuoteStatus.ACTIVE:
            raise AppError(
                "Somente evidências de cotações ativas podem ser inativadas administrativamente.",
                status_code=400,
                code="QUOTE_NOT_EDITABLE",
            )
        evidence = next((e for e in quote.evidences if e.id == evidence_id and e.active), None)
        if evidence is None:
            raise AppError("Evidência não encontrada.", status_code=404, code="NOT_FOUND")

        evidence.active = False
        evidence.deactivated_by = user_id
        evidence.deactivated_at = datetime.now(UTC)
        evidence.deactivation_reason = reason.strip()
        quote.version += 1

        await self.history.record(
            quote_id=quote.id,
            action=QuoteChangeAction.EVIDENCE_REMOVED,
            version=quote.version,
            user_id=user_id,
            reason=reason,
            quote_evidence_id=evidence_id,
            request_id=request_id,
        )
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="quote_evidence",
            entity_id=evidence_id,
            action="deactivate",
            after_data={"reason": reason},
        )
        await self.db.flush()
        return evidence
