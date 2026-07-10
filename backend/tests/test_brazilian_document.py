"""Testes de classificação de documentos brasileiros."""

from app.utils.brazilian_document import (
    DocumentDiagnostic,
    SupplierDocumentType,
    aggregate_document_diagnostics,
    classify_supplier_document,
    validate_cpf,
)


def test_empty_document_is_allowed_type_none() -> None:
    result = classify_supplier_document(None)
    assert result.document_type == SupplierDocumentType.NONE
    assert result.diagnostic == DocumentDiagnostic.EMPTY


def test_valid_cnpj() -> None:
    result = classify_supplier_document("11.222.333/0001-81")
    assert result.document_type == SupplierDocumentType.CNPJ
    assert result.cnpj == "11222333000181"


def test_valid_cpf_not_quarantined() -> None:
    result = classify_supplier_document("529.982.247-25")
    assert result.document_type == SupplierDocumentType.CPF
    assert result.cpf == "52998224725"
    assert result.cnpj is None


def test_validate_cpf_rejects_repeated_digits() -> None:
    assert validate_cpf("00000000000") is False


def test_invalid_cnpj_check_digit() -> None:
    result = classify_supplier_document("11222333000199")
    assert result.document_type == SupplierDocumentType.INVALID
    assert result.diagnostic == DocumentDiagnostic.CHECK_DIGIT_INVALID


def test_fewer_than_14_digits() -> None:
    result = classify_supplier_document("1234567")
    assert result.document_type == SupplierDocumentType.INVALID
    assert result.diagnostic == DocumentDiagnostic.FEWER_THAN_14_DIGITS


def test_aggregate_diagnostics() -> None:
    items = [
        classify_supplier_document(None),
        classify_supplier_document("529.982.247-25"),
        classify_supplier_document("11222333000199"),
    ]
    grouped = aggregate_document_diagnostics(items)
    assert grouped[DocumentDiagnostic.EMPTY.value] == 1
    assert grouped[DocumentDiagnostic.CPF_11_DIGITS.value] == 1
    assert grouped[DocumentDiagnostic.CHECK_DIGIT_INVALID.value] == 1
