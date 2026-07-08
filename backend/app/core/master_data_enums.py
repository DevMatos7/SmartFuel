from enum import StrEnum


class MappingStatus(StrEnum):
    PENDING = "PENDING"
    MAPPED = "MAPPED"
    IGNORED = "IGNORED"
    CONFLICT = "CONFLICT"


class MappingSource(StrEnum):
    MANUAL = "MANUAL"
    CSV = "CSV"
    ERP_SYNC = "ERP_SYNC"


class PaymentType(StrEnum):
    CASH = "CASH"
    TERM = "TERM"
    ANTICIPATED = "ANTICIPATED"


class RegistrationStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class ImportType(StrEnum):
    ERP_PRODUCTS = "ERP_PRODUCTS"
    ERP_SUPPLIERS = "ERP_SUPPLIERS"


class ImportJobStatus(StrEnum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RuleSource(StrEnum):
    PRODUCT_SPECIFIC = "PRODUCT_SPECIFIC"
    DISTRIBUTOR_GENERAL = "DISTRIBUTOR_GENERAL"
    ORGANIZATION_DEFAULT = "ORGANIZATION_DEFAULT"
    NO_RULE = "NO_RULE"
