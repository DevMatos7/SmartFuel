from enum import StrEnum


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class QuoteSourceChannel(StrEnum):
    WHATSAPP = "WHATSAPP"
    PORTAL = "PORTAL"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    OTHER = "OTHER"


class QuoteEntryMethod(StrEnum):
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    API = "API"


class QuoteOrigin(StrEnum):
    MANUAL_OPERATIONAL = "MANUAL_OPERATIONAL"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    LEGACY_DOCUMENTED_IMPORT = "LEGACY_DOCUMENTED_IMPORT"
    API_IMPORT = "API_IMPORT"
    AI_ASSISTED_INGESTION = "AI_ASSISTED_INGESTION"


class FreightType(StrEnum):
    CIF = "CIF"
    FOB = "FOB"


class FreightCalculationType(StrEnum):
    NONE = "NONE"
    TOTAL = "TOTAL"
    PER_LITER = "PER_LITER"


class QuoteEvidenceCategory(StrEnum):
    SCREENSHOT = "SCREENSHOT"
    PORTAL_DOCUMENT = "PORTAL_DOCUMENT"
    EMAIL = "EMAIL"
    SPREADSHEET = "SPREADSHEET"
    PDF_PROPOSAL = "PDF_PROPOSAL"
    OTHER = "OTHER"


class QuoteChangeAction(StrEnum):
    CREATED = "CREATED"
    HEADER_UPDATED = "HEADER_UPDATED"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_UPDATED = "ITEM_UPDATED"
    ITEM_REMOVED = "ITEM_REMOVED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    EVIDENCE_REMOVED = "EVIDENCE_REMOVED"
    ACTIVATED = "ACTIVATED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    REVISION_CREATED = "REVISION_CREATED"
    SUPERSEDED = "SUPERSEDED"
    DUPLICATED = "DUPLICATED"
    SUPPLEMENTAL_EVIDENCE_ADDED = "SUPPLEMENTAL_EVIDENCE_ADDED"


FINAL_QUOTE_STATUSES = frozenset(
    {QuoteStatus.EXPIRED, QuoteStatus.CANCELLED, QuoteStatus.SUPERSEDED}
)

EVIDENCE_REQUIRED_CHANNELS = frozenset(
    {QuoteSourceChannel.WHATSAPP, QuoteSourceChannel.PORTAL, QuoteSourceChannel.EMAIL}
)

ALLOWED_EVIDENCE_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".xlsx", ".csv"}
)

ALLOWED_EVIDENCE_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "application/csv",
    }
)
