"""Testes de migrations Alembic em banco isolado."""

import os

import pytest
from sqlalchemy import create_engine, inspect

from db_guard import validate_test_database_config


EXPECTED_SPRINT2_TABLES = {
    "products",
    "erp_products",
    "product_mapping_history",
    "distributors",
    "erp_suppliers",
    "distribution_bases",
    "payment_terms",
    "station_supplier_rules",
    "master_data_import_jobs",
    "master_data_import_rows",
    "organization_business_settings",
    "quotes",
    "quote_items",
    "quote_evidences",
    "quote_change_history",
    "organization_quote_counters",
}


@pytest.fixture(scope="module")
def sync_url():
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL não configurada")
    _, url = validate_test_database_config()
    return url


def test_migrations_create_sprint2_tables(sync_url, apply_test_migrations) -> None:
    engine = create_engine(sync_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_SPRINT2_TABLES - tables
    assert not missing, f"Tabelas ausentes: {missing}"
    engine.dispose()
