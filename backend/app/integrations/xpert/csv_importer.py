"""Parser e validação de CSVs de cadastros mestres do XPERT."""

from __future__ import annotations

import csv
import io
from typing import Any

from app.core.master_data_enums import ImportType

ERP_PRODUCTS_HEADERS = frozenset(
    {
        "erp_product_id",
        "erp_product_code",
        "erp_description",
        "erp_unit",
        "erp_group_id",
        "erp_group_name",
        "erp_subgroup_id",
        "erp_subgroup_name",
    }
)

ERP_PRODUCTS_REQUIRED_HEADERS = frozenset({"erp_product_id", "erp_description"})

ERP_SUPPLIERS_HEADERS = frozenset(
    {
        "erp_entity_id",
        "erp_entity_code",
        "erp_name",
        "erp_cnpj",
    }
)

ERP_SUPPLIERS_REQUIRED_HEADERS = frozenset({"erp_entity_id", "erp_name"})


def expected_headers(import_type: ImportType) -> frozenset[str]:
    if import_type == ImportType.ERP_PRODUCTS:
        return ERP_PRODUCTS_HEADERS
    if import_type == ImportType.ERP_SUPPLIERS:
        return ERP_SUPPLIERS_HEADERS
    raise ValueError(f"Tipo de importação não suportado: {import_type}")


def required_headers(import_type: ImportType) -> frozenset[str]:
    if import_type == ImportType.ERP_PRODUCTS:
        return ERP_PRODUCTS_REQUIRED_HEADERS
    if import_type == ImportType.ERP_SUPPLIERS:
        return ERP_SUPPLIERS_REQUIRED_HEADERS
    raise ValueError(f"Tipo de importação não suportado: {import_type}")


def parse_csv_content(content: bytes, *, encoding: str = "utf-8-sig") -> tuple[list[str], list[dict[str, str | None]]]:
    text = content.decode(encoding)
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], []

    headers = [h.strip() for h in reader.fieldnames if h and h.strip()]
    rows: list[dict[str, str | None]] = []
    for raw_row in reader:
        if not any(v and str(v).strip() for v in raw_row.values()):
            continue
        row: dict[str, str | None] = {}
        for key in headers:
            value = raw_row.get(key)
            if value is None:
                row[key] = None
            else:
                stripped = str(value).strip()
                row[key] = stripped if stripped else None
        rows.append(row)
    return headers, rows


def validate_headers(headers: list[str], import_type: ImportType) -> list[str]:
    normalized = {h.strip().lower() for h in headers}
    missing = sorted(required_headers(import_type) - normalized)
    return missing


def validate_row(row: dict[str, str | None], import_type: ImportType) -> dict[str, str]:
    errors: dict[str, str] = {}
    normalized = {k.lower(): v for k, v in row.items()}

    if import_type == ImportType.ERP_PRODUCTS:
        erp_id = normalized.get("erp_product_id")
        description = normalized.get("erp_description")
        if not erp_id:
            errors["erp_product_id"] = "Identificador do produto ERP é obrigatório."
        elif len(erp_id) > 100:
            errors["erp_product_id"] = "Identificador do produto ERP excede 100 caracteres."
        if not description:
            errors["erp_description"] = "Descrição do produto ERP é obrigatória."
        elif len(description) > 255:
            errors["erp_description"] = "Descrição excede 255 caracteres."
        for field, max_len in (
            ("erp_product_code", 100),
            ("erp_unit", 30),
            ("erp_group_id", 100),
            ("erp_group_name", 150),
            ("erp_subgroup_id", 100),
            ("erp_subgroup_name", 150),
        ):
            value = normalized.get(field)
            if value and len(value) > max_len:
                errors[field] = f"Campo excede {max_len} caracteres."

    elif import_type == ImportType.ERP_SUPPLIERS:
        entity_id = normalized.get("erp_entity_id")
        name = normalized.get("erp_name")
        if not entity_id:
            errors["erp_entity_id"] = "Identificador da entidade ERP é obrigatório."
        elif len(entity_id) > 100:
            errors["erp_entity_id"] = "Identificador excede 100 caracteres."
        if not name:
            errors["erp_name"] = "Nome da entidade ERP é obrigatório."
        elif len(name) > 255:
            errors["erp_name"] = "Nome excede 255 caracteres."
        cnpj = normalized.get("erp_cnpj")
        if cnpj and len("".join(c for c in cnpj if c.isdigit())) > 14:
            errors["erp_cnpj"] = "CNPJ excede 14 dígitos."
        for field, max_len in (("erp_entity_code", 100),):
            value = normalized.get(field)
            if value and len(value) > max_len:
                errors[field] = f"Campo excede {max_len} caracteres."

    return errors


def normalize_row(row: dict[str, str | None], import_type: ImportType) -> dict[str, Any]:
    normalized = {k.lower(): v for k, v in row.items()}
    if import_type == ImportType.ERP_PRODUCTS:
        return {
            "erp_product_id": normalized.get("erp_product_id"),
            "erp_product_code": normalized.get("erp_product_code"),
            "erp_description": normalized.get("erp_description"),
            "erp_unit": normalized.get("erp_unit"),
            "erp_group_id": normalized.get("erp_group_id"),
            "erp_group_name": normalized.get("erp_group_name"),
            "erp_subgroup_id": normalized.get("erp_subgroup_id"),
            "erp_subgroup_name": normalized.get("erp_subgroup_name"),
        }
    return {
        "erp_entity_id": normalized.get("erp_entity_id"),
        "erp_entity_code": normalized.get("erp_entity_code"),
        "erp_name": normalized.get("erp_name"),
        "erp_cnpj": normalized.get("erp_cnpj"),
    }


def external_identifier(row: dict[str, Any], import_type: ImportType) -> str | None:
    if import_type == ImportType.ERP_PRODUCTS:
        return row.get("erp_product_id")
    return row.get("erp_entity_id")
