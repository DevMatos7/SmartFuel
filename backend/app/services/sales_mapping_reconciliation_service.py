from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cfop_policy import get_cfop_policy
from app.core.fuel_sales_enums import MetricExclusionReason, ReconciliationRunStatus
from app.core.master_data_enums import MappingStatus
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import FuelSalesFact, SalesMappingReconciliationRun
from app.models.product import Product
from app.services.fuel_sales_aggregation_service import FuelSalesAggregationService
from app.services.fuel_sales_apply_service import AffectedAggregationKey, _compute_eligibility, _is_fuel_canonical_product


class SalesMappingReconciliationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.aggregation = FuelSalesAggregationService(db)

    async def reconcile_for_erp_product(
        self,
        *,
        organization_id: uuid.UUID,
        erp_product_id: uuid.UUID,
        requested_by: uuid.UUID | None,
    ) -> SalesMappingReconciliationRun:
        erp_product = await self.db.get(ErpProduct, erp_product_id)
        if erp_product is None or erp_product.organization_id != organization_id:
            raise ValueError("Produto ERP não encontrado.")
        if erp_product.mapping_status != MappingStatus.MAPPED or erp_product.canonical_product_id is None:
            raise ValueError("Produto ERP não está mapeado para produto canônico.")

        run = SalesMappingReconciliationRun(
            organization_id=organization_id,
            status=ReconciliationRunStatus.RUNNING,
            erp_product_id=erp_product_id,
            requested_by=requested_by,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        try:
            facts_result = await self.db.execute(
                select(FuelSalesFact).where(
                    FuelSalesFact.organization_id == organization_id,
                    FuelSalesFact.erp_product_id == erp_product_id,
                    FuelSalesFact.canonical_product_id.is_(None),
                )
            )
            facts = list(facts_result.scalars().all())
            affected_dates: set[date] = set()
            keys: list[AffectedAggregationKey] = []
            canonical_product = await self.db.get(Product, erp_product.canonical_product_id)
            is_fuel_product = _is_fuel_canonical_product(canonical_product)

            for fact in facts:
                fact.canonical_product_id = erp_product.canonical_product_id
                prior_reasons = list(fact.metric_exclusion_reasons or [])
                cost_mismatch = MetricExclusionReason.COST_COMPONENT_MISMATCH.value in prior_reasons
                cfop_policy = get_cfop_policy(fact.source_cfop)
                eligibility, reasons = _compute_eligibility(
                    is_cancelled=fact.is_cancelled,
                    erp_product=erp_product,
                    volume_liters=fact.volume_liters,
                    volume_reason=(
                        MetricExclusionReason.UNIT_CONVERSION_REQUIRED
                        if MetricExclusionReason.UNIT_CONVERSION_REQUIRED.value in prior_reasons
                        else None
                    ),
                    net_amount=fact.net_amount,
                    cost_mismatch=cost_mismatch,
                    payment_method_group=fact.payment_method_group,
                    source_payment_method_id=None,
                    margin_status=fact.margin_status,
                    gross_margin_amount=fact.gross_margin_amount,
                    cfop_policy=cfop_policy,
                    operation_type=fact.operation_type,
                    is_fuel_product=is_fuel_product,
                )
                fact.metric_eligibility_status = eligibility
                fact.metric_exclusion_reasons = [r.value if hasattr(r, "value") else r for r in reasons] or None
                fact.cfop_classification = cfop_policy.treatment.value
                fact.updated_at = datetime.now(UTC)
                affected_dates.add(fact.business_date)

                keys.append(
                    AffectedAggregationKey(
                        station_id=fact.station_id,
                        business_date=fact.business_date,
                        canonical_product_id=erp_product.canonical_product_id,
                        payment_method_group=fact.payment_method_group,
                    )
                )

            unique_keys = list({(k.station_id, k.business_date, k.canonical_product_id, k.payment_method_group): k for k in keys}.values())
            await self.aggregation.rebuild_keys(
                organization_id=organization_id,
                keys=unique_keys,
                sync_run_id=None,
            )

            run.affected_facts = len(facts)
            run.affected_dates = len(affected_dates)
            run.status = ReconciliationRunStatus.COMPLETED
            run.finished_at = datetime.now(UTC)
        except Exception as exc:
            run.status = ReconciliationRunStatus.FAILED
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)[:1000]
            raise
        finally:
            await self.db.flush()

        return run

    async def reconcile_all_pending(
        self,
        *,
        organization_id: uuid.UUID,
        station_ids: list[uuid.UUID],
        requested_by: uuid.UUID | None,
    ) -> list[SalesMappingReconciliationRun]:
        result = await self.db.execute(
            select(ErpProduct).where(
                ErpProduct.organization_id == organization_id,
                ErpProduct.station_id.in_(station_ids),
                ErpProduct.mapping_status == MappingStatus.MAPPED,
                ErpProduct.canonical_product_id.is_not(None),
            )
        )
        products = list(result.scalars().all())
        runs: list[SalesMappingReconciliationRun] = []
        for product in products:
            pending = await self.db.execute(
                select(func.count())
                .select_from(FuelSalesFact)
                .where(
                    FuelSalesFact.erp_product_id == product.id,
                    FuelSalesFact.canonical_product_id.is_(None),
                )
            )
            if int(pending.scalar_one()) == 0:
                continue
            runs.append(
                await self.reconcile_for_erp_product(
                    organization_id=organization_id,
                    erp_product_id=product.id,
                    requested_by=requested_by,
                )
            )
        return runs
