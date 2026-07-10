"""Testes de validação de documentos em fornecedores XPERT."""

from __future__ import annotations

import pytest

from app.core.xpert_sync_enums import ErpDatasetCode, ErpSyncRunStatus
from app.integrations.xpert.fake_datasource import FakeXpertDataSource
from app.services.xpert_sync_service import XpertSyncService
from tests.xpert_helpers import commit_org_context, commit_xpert_bundle


@pytest.mark.asyncio
async def test_supplier_validation_rules(session_factory) -> None:
    ctx = await commit_org_context(session_factory)
    bundle = await commit_xpert_bundle(
        session_factory,
        organization_id=ctx["organization_id"],
        user_id=ctx["user_id"],
        station_id=ctx["station_id"],
        dataset_code=ErpDatasetCode.SUPPLIERS,
    )

    async with session_factory() as session:
        async with session.begin():
            sync = XpertSyncService(session)
            fake = FakeXpertDataSource(
                rows_by_query={
                    "default": [
                        {
                            "source_supplier_id": "1",
                            "source_name": "Sem documento",
                            "source_cnpj": None,
                            "source_active": True,
                        },
                        {
                            "source_supplier_id": "2",
                            "source_name": "Pessoa física",
                            "source_cnpj": "529.982.247-25",
                            "source_active": True,
                        },
                        {
                            "source_supplier_id": "3",
                            "source_name": "CNPJ inválido",
                            "source_cnpj": "11222333000199",
                            "source_active": True,
                        },
                    ]
                }
            )
            processed = await sync.process_run(bundle["run_id"], datasource=fake)
            assert processed.status == ErpSyncRunStatus.PARTIAL
            assert processed.rows_applied == 2
            assert processed.rows_quarantined == 1
