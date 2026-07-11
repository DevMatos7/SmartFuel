"""Enums Sprint 13 — ingestão inteligente de cotações por IA."""

from enum import StrEnum


class QuoteIngestionSourceChannel(StrEnum):
    UPLOAD = "UPLOAD"
    TEXT_PASTE = "TEXT_PASTE"
    IMAGE_CAPTURE = "IMAGE_CAPTURE"
    EMAIL_FILE = "EMAIL_FILE"
    PORTAL_EXPORT = "PORTAL_EXPORT"
    WHATSAPP_SCREENSHOT = "WHATSAPP_SCREENSHOT"
    WHATSAPP_TEXT = "WHATSAPP_TEXT"


class QuoteIngestionDocumentType(StrEnum):
    QUOTE_MESSAGE = "QUOTE_MESSAGE"
    QUOTE_TABLE = "QUOTE_TABLE"
    QUOTE_PDF = "QUOTE_PDF"
    QUOTE_IMAGE = "QUOTE_IMAGE"
    PORTAL_SCREENSHOT = "PORTAL_SCREENSHOT"
    EMAIL_QUOTE = "EMAIL_QUOTE"
    SPREADSHEET_QUOTE = "SPREADSHEET_QUOTE"
    PRICE_UPDATE = "PRICE_UPDATE"
    QUOTE_CORRECTION = "QUOTE_CORRECTION"
    MULTIPLE_QUOTES = "MULTIPLE_QUOTES"
    UNSUPPORTED_DOCUMENT = "UNSUPPORTED_DOCUMENT"
    UNKNOWN_DOCUMENT = "UNKNOWN_DOCUMENT"


class QuoteIngestionBatchStatus(StrEnum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class QuoteIngestionDocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    TEXT_EXTRACTION = "TEXT_EXTRACTION"
    AI_EXTRACTION = "AI_EXTRACTION"
    NORMALIZING = "NORMALIZING"
    VALIDATING_FIELDS = "VALIDATING_FIELDS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    READY_FOR_DRAFT = "READY_FOR_DRAFT"
    DRAFT_CREATED = "DRAFT_CREATED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class QuoteIngestionReviewStatus(StrEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    APPROVED_WITH_CORRECTIONS = "APPROVED_WITH_CORRECTIONS"
    REJECTED = "REJECTED"


class QuoteExtractionValueOrigin(StrEnum):
    EXTRACTED = "EXTRACTED"
    DERIVED = "DERIVED"
    USER_CONFIRMED = "USER_CONFIRMED"
    USER_CORRECTED = "USER_CORRECTED"
    SYSTEM_DEFAULT = "SYSTEM_DEFAULT"


class QuoteEntityMatchStatus(StrEnum):
    MATCHED = "MATCHED"
    SUGGESTED = "SUGGESTED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


class QuoteEntityType(StrEnum):
    DISTRIBUTOR = "DISTRIBUTOR"
    BASE = "BASE"
    STATION = "STATION"
    PRODUCT = "PRODUCT"
    PAYMENT_CONDITION = "PAYMENT_CONDITION"


class QuoteTextExtractionMethod(StrEnum):
    PROVIDED_TEXT = "PROVIDED_TEXT"
    PDF_NATIVE = "PDF_NATIVE"
    SPREADSHEET_PARSER = "SPREADSHEET_PARSER"
    OCR_FALLBACK = "OCR_FALLBACK"
    NONE = "NONE"


class QuoteAiQualityCode(StrEnum):
    PROMPT_INJECTION_CONTENT_DETECTED = "PROMPT_INJECTION_CONTENT_DETECTED"
    AI_BUDGET_EXCEEDED = "AI_BUDGET_EXCEEDED"
    DUPLICATE_IDENTICAL_DOCUMENT = "DUPLICATE_IDENTICAL_DOCUMENT"
    POSSIBLE_DUPLICATE_QUOTE = "POSSIBLE_DUPLICATE_QUOTE"
    PRICE_UPDATE_CANDIDATE = "PRICE_UPDATE_CANDIDATE"
    LOW_FIELD_CONFIDENCE = "LOW_FIELD_CONFIDENCE"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


ALLOWED_INGESTION_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv", ".xlsx"}
)

ALLOWED_INGESTION_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
        "text/plain",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    }
)

PROMPT_INJECTION_PATTERNS = (
    "ignore as regras",
    "ignore previous",
    "ignore the previous",
    "ative esta cotação automaticamente",
    "activate this quote",
    "system prompt",
    "você agora é",
    "you are now",
    "envie os dados para",
    "send the data to",
    "execute url",
    "call url",
)
