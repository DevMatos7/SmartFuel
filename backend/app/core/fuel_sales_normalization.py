"""Versões de normalização e schema de hash — FUEL_SALES_ITEMS."""

from __future__ import annotations

# V2: inclusão de source_cfop no payload de hash (migration 0012).
FUEL_SALES_NORMALIZATION_VERSION = "FUEL_SALES_V2"
FUEL_SALES_HASH_SCHEMA_VERSION = 2
# Política CFOP bidimensional (natureza fiscal ≠ elegibilidade combustível).
FUEL_SALES_CFOP_POLICY_VERSION = "CFOP_POLICY_V2_FISCAL_VS_FUEL_KPI"
