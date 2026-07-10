"""Classificação de documentos brasileiros (CNPJ/CPF) para integração XPERT."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.utils.cnpj import normalize_cnpj, validate_cnpj


class DocumentDiagnostic(StrEnum):
    EMPTY = "EMPTY"
    FEWER_THAN_14_DIGITS = "FEWER_THAN_14_DIGITS"
    CPF_11_DIGITS = "CPF_11_DIGITS"
    REPEATED_DIGITS = "REPEATED_DIGITS"
    CHECK_DIGIT_INVALID = "CHECK_DIGIT_INVALID"
    OTHER_FORMAT = "OTHER_FORMAT"


class SupplierDocumentType(StrEnum):
    NONE = "NONE"
    CNPJ = "CNPJ"
    CPF = "CPF"
    FOREIGN = "FOREIGN"
    INVALID = "INVALID"


@dataclass(frozen=True)
class DocumentClassification:
    document_type: SupplierDocumentType
    diagnostic: DocumentDiagnostic | None
    cnpj: str | None
    cpf: str | None
    raw_digits: str | None


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_cpf(cpf: str) -> bool:
    digits = _only_digits(cpf)
    if len(digits) != 11:
        return False
    if digits == digits[0] * 11:
        return False

    def calc_digit(nums: str, weights: list[int]) -> str:
        total = sum(int(n) * w for n, w in zip(nums, weights, strict=True))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first = calc_digit(digits[:9], list(range(10, 1, -1)))
    second = calc_digit(digits[:9] + first, list(range(11, 1, -1)))
    return digits[-2:] == first + second


def classify_supplier_document(raw_value: str | None) -> DocumentClassification:
    cleaned = (raw_value or "").strip()
    if not cleaned:
        return DocumentClassification(
            document_type=SupplierDocumentType.NONE,
            diagnostic=DocumentDiagnostic.EMPTY,
            cnpj=None,
            cpf=None,
            raw_digits=None,
        )

    digits = _only_digits(cleaned)
    if not digits:
        return DocumentClassification(
            document_type=SupplierDocumentType.NONE,
            diagnostic=DocumentDiagnostic.EMPTY,
            cnpj=None,
            cpf=None,
            raw_digits=None,
        )

    if re.search(r"[A-Za-z]", cleaned) and len(digits) not in (11, 14):
        return DocumentClassification(
            document_type=SupplierDocumentType.FOREIGN,
            diagnostic=DocumentDiagnostic.OTHER_FORMAT,
            cnpj=None,
            cpf=None,
            raw_digits=digits,
        )

    if len(digits) < 11:
        return DocumentClassification(
            document_type=SupplierDocumentType.INVALID,
            diagnostic=DocumentDiagnostic.FEWER_THAN_14_DIGITS,
            cnpj=None,
            cpf=None,
            raw_digits=digits,
        )

    if len(digits) == 11:
        if validate_cpf(digits):
            return DocumentClassification(
                document_type=SupplierDocumentType.CPF,
                diagnostic=DocumentDiagnostic.CPF_11_DIGITS,
                cnpj=None,
                cpf=digits,
                raw_digits=digits,
            )
        diagnostic = (
            DocumentDiagnostic.REPEATED_DIGITS
            if digits == digits[0] * 11
            else DocumentDiagnostic.CHECK_DIGIT_INVALID
        )
        return DocumentClassification(
            document_type=SupplierDocumentType.INVALID,
            diagnostic=diagnostic,
            cnpj=None,
            cpf=None,
            raw_digits=digits,
        )

    if len(digits) in (12, 13):
        return DocumentClassification(
            document_type=SupplierDocumentType.INVALID,
            diagnostic=DocumentDiagnostic.FEWER_THAN_14_DIGITS,
            cnpj=None,
            cpf=None,
            raw_digits=digits,
        )

    if len(digits) == 14:
        if validate_cnpj(digits):
            return DocumentClassification(
                document_type=SupplierDocumentType.CNPJ,
                diagnostic=None,
                cnpj=normalize_cnpj(digits),
                cpf=None,
                raw_digits=digits,
            )
        diagnostic = (
            DocumentDiagnostic.REPEATED_DIGITS
            if digits == digits[0] * 14
            else DocumentDiagnostic.CHECK_DIGIT_INVALID
        )
        return DocumentClassification(
            document_type=SupplierDocumentType.INVALID,
            diagnostic=diagnostic,
            cnpj=None,
            cpf=None,
            raw_digits=digits,
        )

    return DocumentClassification(
        document_type=SupplierDocumentType.INVALID,
        diagnostic=DocumentDiagnostic.OTHER_FORMAT,
        cnpj=None,
        cpf=None,
        raw_digits=digits,
    )


def aggregate_document_diagnostics(classifications: list[DocumentClassification]) -> dict[str, int]:
    buckets = {
        DocumentDiagnostic.EMPTY.value: 0,
        DocumentDiagnostic.FEWER_THAN_14_DIGITS.value: 0,
        DocumentDiagnostic.CPF_11_DIGITS.value: 0,
        DocumentDiagnostic.REPEATED_DIGITS.value: 0,
        DocumentDiagnostic.CHECK_DIGIT_INVALID.value: 0,
        DocumentDiagnostic.OTHER_FORMAT.value: 0,
    }
    for item in classifications:
        if item.document_type == SupplierDocumentType.CPF:
            buckets[DocumentDiagnostic.CPF_11_DIGITS.value] += 1
        elif item.document_type == SupplierDocumentType.NONE:
            buckets[DocumentDiagnostic.EMPTY.value] += 1
        elif item.diagnostic is not None:
            buckets[item.diagnostic.value] += 1
    return {key: value for key, value in buckets.items() if value > 0}
