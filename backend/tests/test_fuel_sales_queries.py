"""Validação estática das queries Sprint 6 — vendas e preços."""

from __future__ import annotations

import pytest

from app.core.xpert_sync_enums import ErpDatasetCode
from app.integrations.xpert.query_contracts import DATASET_CONTRACTS
from app.integrations.xpert.query_validator import validate_parameters, validate_read_only_query
from app.integrations.xpert.secret_resolver import load_query_file


@pytest.mark.parametrize(
    ("query_file", "dataset_code"),
    [
        ("fuel_sales_items.sql", ErpDatasetCode.FUEL_SALES_ITEMS),
        ("payment_methods.sql", ErpDatasetCode.PAYMENT_METHODS),
        ("fuel_retail_prices.sql", ErpDatasetCode.FUEL_RETAIL_PRICES),
    ],
)
def test_sprint6_queries_are_read_only_with_allowed_params(query_file: str, dataset_code: str):
    sql = load_query_file(query_file)
    validation = validate_read_only_query(sql)
    assert validation.valid, validation.errors
    assert validate_parameters(sql) == []


@pytest.mark.parametrize(
    ("query_file", "dataset_code"),
    [
        ("fuel_sales_items.sql", ErpDatasetCode.FUEL_SALES_ITEMS),
        ("payment_methods.sql", ErpDatasetCode.PAYMENT_METHODS),
        ("fuel_retail_prices.sql", ErpDatasetCode.FUEL_RETAIL_PRICES),
    ],
)
def test_sprint6_queries_expose_contract_columns(query_file: str, dataset_code: str):
    sql = load_query_file(query_file).lower()
    contract = DATASET_CONTRACTS[dataset_code]
    for column in contract.required_columns():
        assert column.lower() in sql, f"Coluna obrigatória ausente: {column}"


def test_fuel_sales_query_references_faturamento_tables():
    sql = load_query_file("fuel_sales_items.sql")
    for table in ("ITENSMOVPRODUTOS", "MOVPRODUTOS", "COMPROVANTES"):
        assert table in sql.upper()


def test_fuel_sales_query_uses_incremental_window():
    sql = load_query_file("fuel_sales_items.sql")
    assert "@window_start" in sql
    assert "@window_end" in sql
    assert "@station_erp_id" in sql


def test_fuel_sales_query_enforces_branch_isolation():
    sql = load_query_file("fuel_sales_items.sql").upper()
    assert "@STATION_ERP_ID" in sql
    assert sql.count("ID_FILIAL = @STATION_ERP_ID") >= 3
    assert "PRODUTOS" in sql


def test_fuel_retail_prices_maps_valor_to_formapgto():
    sql = load_query_file("fuel_retail_prices.sql")
    for code in ("'0'", "'1'", "'3'", "'4'"):
        assert code in sql
