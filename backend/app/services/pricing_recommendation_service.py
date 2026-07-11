"""Serviço central Sprint 11 — recomendações de preço (sem escrita no XPERT)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.pricing_enums import (
    CostBasisType,
    CostConfidence,
    DecisionStatus,
    PricingQualityStatus,
    PricingRunStatus,
    PricingScenarioType,
    RecommendationReason,
    RecommendationStatus,
)
from app.domain.pricing.formulas import (
    apply_guardrails,
    apply_rounding,
    build_scenario_price,
    classify_recommendation,
    commercial_floor_price,
    estimated_margin_impact,
    gross_margin_per_liter,
    gross_margin_percentage,
    markup_percentage,
    target_price,
)
from app.domain.quote_comparison.snapshot_canonical import compute_snapshot_hash
from app.models.fuel_purchases import FuelPurchaseInvoice, FuelPurchaseItem
from app.models.fuel_sales import FuelRetailPriceSnapshot
from app.models.pricing import (
    PricingDecision,
    PricingDecisionApproval,
    PricingDecisionEvidence,
    PricingImplementationCheck,
    PricingPolicy,
    PricingRecommendationItem,
    PricingRecommendationRun,
    PricingRecommendationScenario,
)
from app.services.audit_service import AuditContext, AuditService

_ZERO = Decimal("0")
DISCLAIMER = (
    "Margem bruta comercial estimada. Não é lucro líquido. "
    "Recomendação não altera preço no ERP/XPERT."
)


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _parse_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


class PricingRecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ policies
    async def create_policy(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
    ) -> PricingPolicy:
        policy = PricingPolicy(
            id=uuid.uuid4(),
            organization_id=organization_id,
            station_id=data.get("station_id"),
            canonical_product_id=data.get("canonical_product_id"),
            price_type=data.get("price_type", "POSTED_PRICE"),
            name=data["name"],
            status=data.get("status", "ACTIVE"),
            cost_basis_type=data.get("cost_basis_type", CostBasisType.LAST_CONFIRMED_PURCHASE),
            weighted_cost_window_days=data.get("weighted_cost_window_days"),
            minimum_purchase_count=data.get("minimum_purchase_count"),
            minimum_purchase_volume=_dec(data.get("minimum_purchase_volume")),
            minimum_margin_per_liter=_dec(data.get("minimum_margin_per_liter")),
            minimum_margin_percentage=_dec(data.get("minimum_margin_percentage")),
            minimum_markup_percentage=_dec(data.get("minimum_markup_percentage")),
            target_margin_per_liter=_dec(data.get("target_margin_per_liter")),
            target_margin_percentage=_dec(data.get("target_margin_percentage")),
            target_markup_percentage=_dec(data.get("target_markup_percentage")),
            maximum_increase_per_liter=_dec(data.get("maximum_increase_per_liter")),
            maximum_decrease_per_liter=_dec(data.get("maximum_decrease_per_liter")),
            maximum_increase_percentage=_dec(data.get("maximum_increase_percentage")),
            maximum_decrease_percentage=_dec(data.get("maximum_decrease_percentage")),
            minimum_change_per_liter=_dec(data.get("minimum_change_per_liter")),
            rounding_policy=data.get("rounding_policy", "NEAREST_CENT"),
            rounding_increment=_dec(data.get("rounding_increment")),
            default_scenario=data.get("default_scenario", PricingScenarioType.BALANCED),
            allow_low_confidence_cost=bool(data.get("allow_low_confidence_cost", False)),
            require_market_signal=bool(data.get("require_market_signal", False)),
            require_evidence_on_approve=bool(data.get("require_evidence_on_approve", False)),
            allow_self_approval=bool(data.get("allow_self_approval", False)),
            required_approvals=int(data.get("required_approvals", 1)),
            implementation_tolerance_per_liter=_dec(
                data.get("implementation_tolerance_per_liter")
            )
            or Decimal("0.01"),
            valid_from=_parse_dt(data.get("valid_from")) or datetime.now(UTC),
            valid_until=_parse_dt(data.get("valid_until")),
            active=bool(data.get("active", True)),
            created_by=user_id,
        )
        self.db.add(policy)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_policy",
                entity_id=policy.id,
                action="CREATE",
                after_data={"name": policy.name, "cost_basis_type": policy.cost_basis_type},
            )
        return policy

    async def list_policies(self, organization_id: uuid.UUID) -> list[PricingPolicy]:
        result = await self.db.execute(
            select(PricingPolicy)
            .where(PricingPolicy.organization_id == organization_id)
            .order_by(PricingPolicy.valid_from.desc())
        )
        return list(result.scalars().all())

    async def get_policy(self, policy_id: uuid.UUID, organization_id: uuid.UUID) -> PricingPolicy:
        result = await self.db.execute(
            select(PricingPolicy).where(
                PricingPolicy.id == policy_id,
                PricingPolicy.organization_id == organization_id,
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            raise AppError("Política não encontrada.", status_code=404, code="NOT_FOUND")
        return policy

    async def deactivate_policy(
        self,
        policy_id: uuid.UUID,
        organization_id: uuid.UUID,
        audit_ctx: AuditContext | None = None,
    ) -> PricingPolicy:
        policy = await self.get_policy(policy_id, organization_id)
        policy.active = False
        policy.status = "INACTIVE"
        policy.valid_until = datetime.now(UTC)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_policy",
                entity_id=policy.id,
                action="DEACTIVATE",
            )
        return policy

    async def resolve_policy(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID | None,
        product_id: uuid.UUID | None,
        price_type: str,
        reference_datetime: datetime,
        synthetic_policy: dict[str, Any] | None = None,
    ) -> PricingPolicy | dict[str, Any] | None:
        if synthetic_policy is not None:
            return synthetic_policy

        result = await self.db.execute(
            select(PricingPolicy)
            .where(
                PricingPolicy.organization_id == organization_id,
                PricingPolicy.active.is_(True),
                PricingPolicy.price_type == price_type,
                PricingPolicy.valid_from <= reference_datetime,
                or_(
                    PricingPolicy.valid_until.is_(None),
                    PricingPolicy.valid_until > reference_datetime,
                ),
            )
            .order_by(
                # mais específico primeiro
                PricingPolicy.station_id.is_not(None).desc(),
                PricingPolicy.canonical_product_id.is_not(None).desc(),
                PricingPolicy.valid_from.desc(),
            )
        )
        candidates = list(result.scalars().all())
        for p in candidates:
            if station_id and p.station_id and p.station_id != station_id:
                continue
            if product_id and p.canonical_product_id and p.canonical_product_id != product_id:
                continue
            if p.station_id is None or p.station_id == station_id:
                if p.canonical_product_id is None or p.canonical_product_id == product_id:
                    return p
        return candidates[0] if candidates else None

    # ------------------------------------------------------------------ cost / price
    async def resolve_cost_basis(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        product_id: uuid.UUID,
        reference_datetime: datetime,
        policy: PricingPolicy | dict[str, Any],
        synthetic: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if synthetic is not None:
            cost = _dec(synthetic.get("cost_per_liter"))
            if cost is None:
                return {
                    "cost_basis_type": CostBasisType.SYNTHETIC_COST,
                    "cost_per_liter": None,
                    "cost_datetime": None,
                    "cost_available_at": None,
                    "cost_confidence": CostConfidence.UNAVAILABLE,
                    "warnings": [RecommendationReason.MISSING_COST],
                    "details": {"synthetic": True},
                }
            available_at = _parse_dt(synthetic.get("cost_available_at")) or reference_datetime
            if available_at > reference_datetime:
                return {
                    "cost_basis_type": CostBasisType.SYNTHETIC_COST,
                    "cost_per_liter": None,
                    "cost_datetime": None,
                    "cost_available_at": available_at.isoformat(),
                    "cost_confidence": CostConfidence.UNAVAILABLE,
                    "warnings": ["HINDSIGHT_BLOCKED", RecommendationReason.MISSING_COST],
                    "details": {"synthetic": True, "blocked_available_at": available_at.isoformat()},
                }
            return {
                "cost_basis_type": synthetic.get("cost_basis_type", CostBasisType.SYNTHETIC_COST),
                "cost_per_liter": cost,
                "cost_datetime": (_parse_dt(synthetic.get("cost_datetime")) or available_at).isoformat(),
                "cost_available_at": available_at.isoformat(),
                "cost_confidence": synthetic.get("cost_confidence", CostConfidence.HIGH),
                "warnings": list(synthetic.get("warnings") or []),
                "details": {"synthetic": True, **(synthetic.get("details") or {})},
                "replacement_cost": _dec(synthetic.get("replacement_cost")),
            }

        basis = (
            policy.cost_basis_type
            if isinstance(policy, PricingPolicy)
            else policy.get("cost_basis_type", CostBasisType.LAST_CONFIRMED_PURCHASE)
        )
        window_days = (
            policy.weighted_cost_window_days
            if isinstance(policy, PricingPolicy)
            else policy.get("weighted_cost_window_days")
        ) or 30

        purchase_q = (
            select(FuelPurchaseItem, FuelPurchaseInvoice)
            .join(
                FuelPurchaseInvoice,
                FuelPurchaseItem.purchase_invoice_id == FuelPurchaseInvoice.id,
            )
            .where(
                FuelPurchaseItem.organization_id == organization_id,
                FuelPurchaseItem.station_id == station_id,
                FuelPurchaseItem.canonical_product_id == product_id,
                FuelPurchaseInvoice.is_cancelled.is_(False),
                FuelPurchaseItem.volume_liters.is_not(None),
                FuelPurchaseItem.volume_liters > 0,
                FuelPurchaseItem.commercial_delivered_cost.is_not(None),
                FuelPurchaseInvoice.entry_date <= reference_datetime.date(),
            )
            .order_by(FuelPurchaseInvoice.entry_date.desc(), FuelPurchaseItem.created_at.desc())
        )
        rows = list((await self.db.execute(purchase_q)).all())

        last_cost = None
        last_dt = None
        if rows:
            item, inv = rows[0]
            if item.volume_liters and item.commercial_delivered_cost is not None:
                last_cost = item.commercial_delivered_cost / item.volume_liters
                last_dt = datetime.combine(inv.entry_date, datetime.min.time(), tzinfo=UTC)

        weighted = None
        if basis in (CostBasisType.WEIGHTED_PURCHASE_COST, CostBasisType.CONSERVATIVE_MAX):
            cutoff = reference_datetime - timedelta(days=int(window_days))
            total_cost = _ZERO
            total_vol = _ZERO
            for item, inv in rows:
                inv_dt = datetime.combine(inv.entry_date, datetime.min.time(), tzinfo=UTC)
                if inv_dt < cutoff:
                    continue
                if item.commercial_delivered_cost is None or not item.volume_liters:
                    continue
                total_cost += item.commercial_delivered_cost
                total_vol += item.volume_liters
            if total_vol > _ZERO:
                weighted = total_cost / total_vol

        # Quote-based bases: reuse is deferred to QuoteCandidateService in future real homologation.
        # For foundation, missing quote → UNAVAILABLE unless purchase exists for CONSERVATIVE_MAX.
        replacement = _dec(
            None
        )  # placeholder; synthetic path covers quote scenarios in homologação sintética

        cost = None
        confidence = CostConfidence.UNAVAILABLE
        cost_dt = last_dt
        warnings: list[str] = []

        if basis == CostBasisType.LAST_CONFIRMED_PURCHASE:
            cost = last_cost
            confidence = CostConfidence.HIGH if cost is not None else CostConfidence.UNAVAILABLE
        elif basis == CostBasisType.WEIGHTED_PURCHASE_COST:
            cost = weighted
            confidence = CostConfidence.HIGH if cost is not None else CostConfidence.UNAVAILABLE
        elif basis == CostBasisType.CONSERVATIVE_MAX:
            candidates = [c for c in (last_cost, weighted, replacement) if c is not None]
            cost = max(candidates) if candidates else None
            confidence = CostConfidence.HIGH if cost is not None else CostConfidence.UNAVAILABLE
        elif basis in (
            CostBasisType.BEST_CURRENT_ELIGIBLE_QUOTE,
            CostBasisType.AVERAGE_ELIGIBLE_QUOTE,
        ):
            warnings.append("QUOTE_COST_REQUIRES_HOMOLOGATED_ENGINE")
            cost = last_cost  # fallback transparente com warning
            confidence = CostConfidence.MEDIUM if cost is not None else CostConfidence.UNAVAILABLE
        else:
            cost = last_cost
            confidence = CostConfidence.MEDIUM if cost is not None else CostConfidence.UNAVAILABLE

        if cost is None:
            warnings.append(RecommendationReason.MISSING_COST)

        age_days = None
        if cost_dt:
            age_days = (reference_datetime - cost_dt).days
            if age_days > 45:
                warnings.append(RecommendationReason.STALE_COST)
                if confidence == CostConfidence.HIGH:
                    confidence = CostConfidence.MEDIUM

        return {
            "cost_basis_type": basis,
            "cost_per_liter": cost,
            "cost_datetime": cost_dt.isoformat() if cost_dt else None,
            "cost_available_at": cost_dt.isoformat() if cost_dt else None,
            "cost_confidence": confidence,
            "cost_age_days": age_days,
            "warnings": warnings,
            "details": {
                "last_purchase_cost": str(last_cost) if last_cost is not None else None,
                "weighted_cost": str(weighted) if weighted is not None else None,
            },
            "replacement_cost": replacement,
        }

    async def resolve_current_price(
        self,
        *,
        organization_id: uuid.UUID,
        station_id: uuid.UUID,
        product_id: uuid.UUID,
        reference_datetime: datetime,
        synthetic: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if synthetic is not None:
            price = _dec(synthetic.get("current_price"))
            available_at = _parse_dt(synthetic.get("current_price_available_at")) or reference_datetime
            if price is None:
                return {
                    "current_price": None,
                    "current_price_source": None,
                    "current_price_datetime": None,
                    "current_price_available_at": None,
                    "current_price_confidence": CostConfidence.UNAVAILABLE,
                    "warnings": [RecommendationReason.MISSING_CURRENT_PRICE],
                }
            if available_at > reference_datetime:
                return {
                    "current_price": None,
                    "current_price_source": synthetic.get("current_price_source"),
                    "current_price_datetime": None,
                    "current_price_available_at": available_at.isoformat(),
                    "current_price_confidence": CostConfidence.UNAVAILABLE,
                    "warnings": ["HINDSIGHT_BLOCKED", RecommendationReason.MISSING_CURRENT_PRICE],
                }
            warnings = list(synthetic.get("warnings") or [])
            age = (reference_datetime - available_at).days
            if age > 7:
                warnings.append("STALE_CURRENT_PRICE")
            return {
                "current_price": price,
                "current_price_source": synthetic.get(
                    "current_price_source", "MANUAL_CONFIRMED_PRICE"
                ),
                "current_price_datetime": (
                    _parse_dt(synthetic.get("current_price_datetime")) or available_at
                ).isoformat(),
                "current_price_available_at": available_at.isoformat(),
                "current_price_confidence": synthetic.get("current_price_confidence", "HIGH"),
                "warnings": warnings,
            }

        result = await self.db.execute(
            select(FuelRetailPriceSnapshot)
            .where(
                FuelRetailPriceSnapshot.organization_id == organization_id,
                FuelRetailPriceSnapshot.station_id == station_id,
                FuelRetailPriceSnapshot.canonical_product_id == product_id,
                FuelRetailPriceSnapshot.effective_from <= reference_datetime,
                or_(
                    FuelRetailPriceSnapshot.effective_until.is_(None),
                    FuelRetailPriceSnapshot.effective_until > reference_datetime,
                ),
                FuelRetailPriceSnapshot.observed_at <= reference_datetime,
            )
            .order_by(FuelRetailPriceSnapshot.effective_from.desc())
            .limit(1)
        )
        snap = result.scalar_one_or_none()
        if not snap:
            return {
                "current_price": None,
                "current_price_source": None,
                "current_price_datetime": None,
                "current_price_available_at": None,
                "current_price_confidence": CostConfidence.UNAVAILABLE,
                "warnings": [RecommendationReason.MISSING_CURRENT_PRICE],
            }
        warnings: list[str] = []
        age = (reference_datetime - snap.observed_at).days
        if age > 7:
            warnings.append("STALE_CURRENT_PRICE")
        return {
            "current_price": snap.price_per_liter,
            "current_price_source": "ERP_RETAIL_PRICE_SNAPSHOT",
            "current_price_datetime": snap.effective_from.isoformat(),
            "current_price_available_at": snap.observed_at.isoformat(),
            "current_price_confidence": "HIGH",
            "warnings": warnings,
            "price_snapshot_id": str(snap.id),
        }

    # ------------------------------------------------------------------ compute item
    def compute_recommendation_item(
        self,
        *,
        policy: PricingPolicy | dict[str, Any],
        cost_info: dict[str, Any],
        price_info: dict[str, Any],
        market_signal: dict[str, Any] | None = None,
        reference_volume: Decimal | None = None,
    ) -> dict[str, Any]:
        def pol(attr: str, default=None):
            if isinstance(policy, PricingPolicy):
                return getattr(policy, attr, default)
            return policy.get(attr, default)

        cost = _dec(cost_info.get("cost_per_liter"))
        price = _dec(price_info.get("current_price"))
        warnings = list(cost_info.get("warnings") or []) + list(price_info.get("warnings") or [])
        reasons: list[str] = []
        quality = PricingQualityStatus.READY

        if cost is None:
            reasons.append(RecommendationReason.MISSING_COST)
            quality = PricingQualityStatus.MISSING_COST
        if price is None:
            reasons.append(RecommendationReason.MISSING_CURRENT_PRICE)
            if quality == PricingQualityStatus.READY:
                quality = PricingQualityStatus.MISSING_PRICE

        if cost is not None and cost_info.get("cost_confidence") == CostConfidence.LOW:
            if not pol("allow_low_confidence_cost"):
                reasons.append(RecommendationReason.LOW_COST_CONFIDENCE)
                quality = PricingQualityStatus.LOW_COST_CONFIDENCE
            else:
                warnings.append(RecommendationReason.LOW_COST_CONFIDENCE)
                quality = PricingQualityStatus.READY_WITH_WARNINGS

        if RecommendationReason.STALE_COST in warnings:
            if quality == PricingQualityStatus.READY:
                quality = PricingQualityStatus.STALE_COST
        if "STALE_CURRENT_PRICE" in warnings:
            reasons.append(RecommendationReason.STALE_PRICE)
            if quality == PricingQualityStatus.READY:
                quality = PricingQualityStatus.STALE_PRICE

        market_advisory: dict[str, Any] | None = None
        if market_signal:
            market_advisory = {
                **market_signal,
                "advisory_only": True,
                "note": "Sinal consultivo. Não aplica multiplicador automático.",
            }
            mq = market_signal.get("quality") or market_signal.get("market_signal_quality")
            if mq in ("INSUFFICIENT_SAMPLE", "LOW_COVERAGE", "STALE_SOURCE"):
                warnings.append(RecommendationReason.MARKET_SIGNAL_WARNING)
            elif market_signal.get("market_direction") in ("UP", "DOWN", "MIXED"):
                warnings.append("MARKET_SIGNAL_ADVISORY")

        if cost is None or price is None:
            return {
                "current_price": price,
                "cost_per_liter": cost,
                "cost_basis_type": cost_info.get("cost_basis_type"),
                "cost_confidence": cost_info.get("cost_confidence", CostConfidence.UNAVAILABLE),
                "current_margin_per_liter": None,
                "current_margin_percentage": None,
                "current_markup_percentage": None,
                "commercial_floor_price": None,
                "target_price": None,
                "raw_recommended_price": None,
                "recommended_price": None,
                "recommended_change_per_liter": None,
                "recommended_change_percentage": None,
                "recommendation_status": RecommendationStatus.NO_RECOMMENDATION,
                "quality_status": quality,
                "guardrail_applied": False,
                "rounding_policy": pol("rounding_policy"),
                "reasons": reasons,
                "warnings": warnings,
                "scenarios": [],
                "market_signal": market_advisory,
                "estimated_impact": None,
            }

        margin_l = gross_margin_per_liter(price, cost)
        margin_pct = gross_margin_percentage(price, cost)
        markup = markup_percentage(price, cost)

        floor = commercial_floor_price(
            cost,
            minimum_margin_per_liter=_dec(pol("minimum_margin_per_liter")),
            minimum_margin_percentage=_dec(pol("minimum_margin_percentage")),
            minimum_markup_percentage=_dec(pol("minimum_markup_percentage")),
        )
        tgt = target_price(
            cost,
            target_margin_per_liter=_dec(pol("target_margin_per_liter")),
            target_margin_percentage=_dec(pol("target_margin_percentage")),
            target_markup_percentage=_dec(pol("target_markup_percentage")),
            floor=floor,
        )

        replacement = _dec(cost_info.get("replacement_cost"))
        conservative_cost = cost
        if replacement is not None:
            conservative_cost = max(cost, replacement)
            if replacement > cost:
                reasons.append(RecommendationReason.REPLACEMENT_COST_INCREASED)
            elif replacement < cost:
                reasons.append(RecommendationReason.REPLACEMENT_COST_DECREASED)

        scenarios = []
        for stype in (
            PricingScenarioType.CONSERVATIVE,
            PricingScenarioType.BALANCED,
            PricingScenarioType.COMPETITIVE,
        ):
            calc = build_scenario_price(
                cost,
                floor=floor,
                target=tgt,
                scenario_type=stype,
                conservative_cost=conservative_cost,
            )
            before, rounded = apply_rounding(
                calc,
                pol("rounding_policy") or "NEAREST_CENT",
                increment=_dec(pol("rounding_increment")),
                floor=floor,
            )
            sm = gross_margin_per_liter(rounded, cost) or _ZERO
            scenarios.append(
                {
                    "scenario_type": stype,
                    "cost_per_liter": cost,
                    "margin_per_liter": sm,
                    "margin_percentage": gross_margin_percentage(rounded, cost),
                    "markup_percentage": markup_percentage(rounded, cost),
                    "calculated_price": before,
                    "rounded_price": rounded,
                    "details": {
                        "price_before_rounding": str(before),
                        "price_after_rounding": str(rounded),
                        "rounding_difference": str(rounded - before),
                    },
                }
            )

        default_scenario = pol("default_scenario") or PricingScenarioType.BALANCED
        chosen = next((s for s in scenarios if s["scenario_type"] == default_scenario), scenarios[1])
        raw_rec = chosen["rounded_price"]

        guard = apply_guardrails(
            price,
            raw_rec,
            maximum_increase_per_liter=_dec(pol("maximum_increase_per_liter")),
            maximum_decrease_per_liter=_dec(pol("maximum_decrease_per_liter")),
            maximum_increase_percentage=_dec(pol("maximum_increase_percentage")),
            maximum_decrease_percentage=_dec(pol("maximum_decrease_percentage")),
            minimum_change_per_liter=_dec(pol("minimum_change_per_liter")),
        )
        final_price = guard.guarded_recommended_price
        # re-apply rounding after guardrail and enforce floor
        _, final_price = apply_rounding(
            final_price,
            pol("rounding_policy") or "NEAREST_CENT",
            increment=_dec(pol("rounding_increment")),
            floor=floor,
        )

        extra = list(reasons)
        if guard.reasons:
            extra.extend(guard.reasons)
        status, all_reasons = classify_recommendation(
            price,
            final_price,
            floor=floor,
            target=tgt,
            extra_reasons=extra,
            force_status=guard.status_hint,
        )
        if warnings and quality == PricingQualityStatus.READY:
            quality = PricingQualityStatus.READY_WITH_WARNINGS

        change = final_price - price
        change_pct = (change / price) if price > _ZERO else None
        impact = estimated_margin_impact(change, reference_volume)

        return {
            "current_price": price,
            "cost_per_liter": cost,
            "cost_basis_type": cost_info.get("cost_basis_type"),
            "cost_confidence": cost_info.get("cost_confidence"),
            "cost_datetime": cost_info.get("cost_datetime"),
            "current_margin_per_liter": margin_l,
            "current_margin_percentage": margin_pct,
            "current_markup_percentage": markup,
            "commercial_floor_price": floor,
            "target_price": tgt,
            "raw_recommended_price": guard.raw_recommended_price,
            "recommended_price": final_price,
            "recommended_change_per_liter": change,
            "recommended_change_percentage": change_pct,
            "recommendation_status": status,
            "quality_status": quality,
            "guardrail_applied": guard.guardrail_applied,
            "guardrail_reason": guard.guardrail_reason,
            "rounding_policy": pol("rounding_policy"),
            "reasons": all_reasons,
            "warnings": warnings,
            "scenarios": scenarios,
            "market_signal": market_advisory,
            "estimated_impact": impact,
            "selected_scenario": default_scenario,
        }

    # ------------------------------------------------------------------ runs
    async def run_recommendations(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
    ) -> PricingRecommendationRun:
        now = datetime.now(UTC)
        reference = _parse_dt(data.get("reference_datetime")) or now
        price_type = data.get("price_type", "POSTED_PRICE")
        if price_type != "POSTED_PRICE" and not data.get("allow_non_posted"):
            raise AppError(
                "Enquanto formas de pagamento não estiverem homologadas, use POSTED_PRICE.",
                status_code=400,
                code="PRICE_TYPE_NOT_HOMOLOGATED",
            )

        run = PricingRecommendationRun(
            id=uuid.uuid4(),
            organization_id=organization_id,
            status=PricingRunStatus.RUNNING,
            trigger_type=data.get("trigger_type", "MANUAL"),
            reference_datetime=reference,
            station_id=data.get("station_id"),
            canonical_product_id=data.get("canonical_product_id"),
            price_type=price_type,
            requested_by=user_id,
            reprocess_of_run_id=data.get("reprocess_of_run_id"),
            reprocess_reason=data.get("reprocess_reason"),
            input_snapshot=_jsonable(data),
            interpretive_disclaimer=DISCLAIMER,
            started_at=now,
            created_at=now,
        )
        self.db.add(run)
        await self.db.flush()

        items_spec = data.get("items") or []
        if not items_spec and data.get("station_id") and data.get("canonical_product_id"):
            items_spec = [
                {
                    "station_id": data["station_id"],
                    "canonical_product_id": data["canonical_product_id"],
                    "synthetic_cost": data.get("synthetic_cost"),
                    "synthetic_price": data.get("synthetic_price"),
                    "synthetic_policy": data.get("synthetic_policy"),
                    "market_signal": data.get("market_signal"),
                    "reference_daily_volume": data.get("reference_daily_volume"),
                }
            ]

        warning_count = 0
        error_count = 0
        recommendation_count = 0
        output_items: list[dict[str, Any]] = []

        for spec in items_spec:
            station_id = uuid.UUID(str(spec["station_id"]))
            product_id = uuid.UUID(str(spec["canonical_product_id"]))
            syn_pol = spec.get("synthetic_policy") or data.get("synthetic_policy")
            policy = await self.resolve_policy(
                organization_id=organization_id,
                station_id=station_id,
                product_id=product_id,
                price_type=price_type,
                reference_datetime=reference,
                synthetic_policy=syn_pol,
            )
            if policy is None:
                result = {
                    "recommendation_status": RecommendationStatus.NO_RECOMMENDATION,
                    "quality_status": PricingQualityStatus.POLICY_NOT_FOUND,
                    "reasons": [RecommendationReason.POLICY_NOT_FOUND],
                    "warnings": [],
                    "scenarios": [],
                    "current_price": None,
                    "cost_per_liter": None,
                    "cost_basis_type": CostBasisType.LAST_CONFIRMED_PURCHASE,
                    "cost_confidence": CostConfidence.UNAVAILABLE,
                }
                error_count += 1
            else:
                cost_info = await self.resolve_cost_basis(
                    organization_id=organization_id,
                    station_id=station_id,
                    product_id=product_id,
                    reference_datetime=reference,
                    policy=policy,
                    synthetic=spec.get("synthetic_cost"),
                )
                price_info = await self.resolve_current_price(
                    organization_id=organization_id,
                    station_id=station_id,
                    product_id=product_id,
                    reference_datetime=reference,
                    synthetic=spec.get("synthetic_price"),
                )
                result = self.compute_recommendation_item(
                    policy=policy,
                    cost_info=cost_info,
                    price_info=price_info,
                    market_signal=spec.get("market_signal"),
                    reference_volume=_dec(spec.get("reference_daily_volume")),
                )
                result["policy_snapshot"] = (
                    {
                        "id": str(policy.id),
                        "name": policy.name,
                        "cost_basis_type": policy.cost_basis_type,
                        "valid_from": policy.valid_from.isoformat(),
                    }
                    if isinstance(policy, PricingPolicy)
                    else {"synthetic": True, **{k: str(v) if isinstance(v, Decimal) else v for k, v in policy.items()}}
                )
                result["cost_info"] = {
                    **cost_info,
                    "cost_per_liter": str(cost_info["cost_per_liter"])
                    if cost_info.get("cost_per_liter") is not None
                    else None,
                }
                result["price_info"] = {
                    **price_info,
                    "current_price": str(price_info["current_price"])
                    if price_info.get("current_price") is not None
                    else None,
                }

            if result.get("warnings"):
                warning_count += len(result["warnings"])
            if result.get("recommendation_status") != RecommendationStatus.NO_RECOMMENDATION:
                recommendation_count += 1

            input_snap = {
                "station_id": str(station_id),
                "canonical_product_id": str(product_id),
                "reference_datetime": reference.isoformat(),
                "price_type": price_type,
                "cost_info": result.get("cost_info"),
                "price_info": result.get("price_info"),
                "policy": result.get("policy_snapshot"),
                "market_signal": result.get("market_signal"),
            }
            result_snap = {
                k: (str(v) if isinstance(v, Decimal) else v)
                for k, v in result.items()
                if k not in ("scenarios", "cost_info", "price_info", "policy_snapshot")
            }
            scenarios_snap = [
                {
                    **{kk: (str(vv) if isinstance(vv, Decimal) else vv) for kk, vv in s.items() if kk != "details"},
                    "details": s.get("details"),
                }
                for s in result.get("scenarios") or []
            ]
            result_snap["scenarios"] = scenarios_snap
            digest = compute_snapshot_hash({"input": input_snap, "result": result_snap})

            item = PricingRecommendationItem(
                id=uuid.uuid4(),
                recommendation_run_id=run.id,
                organization_id=organization_id,
                station_id=station_id,
                canonical_product_id=product_id,
                price_type=price_type,
                reference_datetime=reference,
                current_price=_dec(result.get("current_price")),
                current_price_source=(result.get("price_info") or {}).get("current_price_source")
                if result.get("price_info")
                else None,
                current_price_datetime=_parse_dt(
                    (result.get("price_info") or {}).get("current_price_datetime")
                ),
                cost_basis_type=result.get("cost_basis_type") or CostBasisType.LAST_CONFIRMED_PURCHASE,
                cost_per_liter=_dec(result.get("cost_per_liter")),
                cost_datetime=_parse_dt(result.get("cost_datetime")),
                cost_confidence=result.get("cost_confidence") or CostConfidence.UNAVAILABLE,
                current_margin_per_liter=_dec(result.get("current_margin_per_liter")),
                current_margin_percentage=_dec(result.get("current_margin_percentage")),
                current_markup_percentage=_dec(result.get("current_markup_percentage")),
                commercial_floor_price=_dec(result.get("commercial_floor_price")),
                target_price=_dec(result.get("target_price")),
                raw_recommended_price=_dec(result.get("raw_recommended_price")),
                recommended_price=_dec(result.get("recommended_price")),
                recommended_change_per_liter=_dec(result.get("recommended_change_per_liter")),
                recommended_change_percentage=_dec(result.get("recommended_change_percentage")),
                recommendation_status=result.get("recommendation_status"),
                quality_status=result.get("quality_status"),
                guardrail_applied=bool(result.get("guardrail_applied")),
                rounding_policy=result.get("rounding_policy"),
                reasons=result.get("reasons"),
                warnings=result.get("warnings"),
                input_snapshot=input_snap,
                result_snapshot=result_snap,
                snapshot_hash=digest,
                created_at=now,
            )
            self.db.add(item)
            await self.db.flush()

            for s in result.get("scenarios") or []:
                self.db.add(
                    PricingRecommendationScenario(
                        id=uuid.uuid4(),
                        recommendation_item_id=item.id,
                        scenario_type=s["scenario_type"],
                        cost_per_liter=_dec(s["cost_per_liter"]) or _ZERO,
                        margin_per_liter=_dec(s["margin_per_liter"]) or _ZERO,
                        margin_percentage=_dec(s.get("margin_percentage")),
                        markup_percentage=_dec(s.get("markup_percentage")),
                        calculated_price=_dec(s["calculated_price"]) or _ZERO,
                        rounded_price=_dec(s["rounded_price"]) or _ZERO,
                        details=s.get("details"),
                        created_at=now,
                    )
                )

            output_items.append(
                {
                    "id": str(item.id),
                    "recommendation_status": item.recommendation_status,
                    "quality_status": item.quality_status,
                    "recommended_price": str(item.recommended_price)
                    if item.recommended_price is not None
                    else None,
                    "snapshot_hash": digest,
                }
            )

        run.item_count = len(items_spec)
        run.recommendation_count = recommendation_count
        run.warning_count = warning_count
        run.error_count = error_count
        run.output_snapshot = {"items": output_items, "disclaimer": DISCLAIMER}
        run.snapshot_hash = compute_snapshot_hash(run.output_snapshot)
        run.status = PricingRunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        await self.db.flush()

        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_recommendation_run",
                entity_id=run.id,
                action="GENERATE",
                after_data={"item_count": run.item_count, "status": run.status},
            )
        return run

    async def list_runs(self, organization_id: uuid.UUID) -> list[PricingRecommendationRun]:
        result = await self.db.execute(
            select(PricingRecommendationRun)
            .where(PricingRecommendationRun.organization_id == organization_id)
            .order_by(PricingRecommendationRun.created_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def get_run(
        self, run_id: uuid.UUID, organization_id: uuid.UUID
    ) -> PricingRecommendationRun:
        result = await self.db.execute(
            select(PricingRecommendationRun).where(
                PricingRecommendationRun.id == run_id,
                PricingRecommendationRun.organization_id == organization_id,
            )
        )
        run = result.scalar_one_or_none()
        if not run:
            raise AppError("Run não encontrada.", status_code=404, code="NOT_FOUND")
        return run

    async def reprocess_run(
        self,
        *,
        run_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        reason: str,
        audit_ctx: AuditContext | None = None,
    ) -> PricingRecommendationRun:
        original = await self.get_run(run_id, organization_id)
        data = dict(original.input_snapshot or {})
        data["reprocess_of_run_id"] = original.id
        data["reprocess_reason"] = reason
        data["trigger_type"] = "REPROCESS"
        return await self.run_recommendations(
            organization_id=organization_id,
            user_id=user_id,
            data=data,
            audit_ctx=audit_ctx,
        )

    async def list_items(
        self,
        organization_id: uuid.UUID,
        *,
        station_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[PricingRecommendationItem]:
        q = select(PricingRecommendationItem).where(
            PricingRecommendationItem.organization_id == organization_id
        )
        if station_id:
            q = q.where(PricingRecommendationItem.station_id == station_id)
        if status:
            q = q.where(PricingRecommendationItem.recommendation_status == status)
        q = q.order_by(PricingRecommendationItem.created_at.desc()).limit(200)
        return list((await self.db.execute(q)).scalars().all())

    async def get_item(
        self, item_id: uuid.UUID, organization_id: uuid.UUID
    ) -> PricingRecommendationItem:
        result = await self.db.execute(
            select(PricingRecommendationItem).where(
                PricingRecommendationItem.id == item_id,
                PricingRecommendationItem.organization_id == organization_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise AppError("Recomendação não encontrada.", status_code=404, code="NOT_FOUND")
        return item

    async def list_scenarios(
        self, item_id: uuid.UUID
    ) -> list[PricingRecommendationScenario]:
        result = await self.db.execute(
            select(PricingRecommendationScenario).where(
                PricingRecommendationScenario.recommendation_item_id == item_id
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------ decisions / workflow
    async def create_decision(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        item_id: uuid.UUID,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecision:
        item = await self.get_item(item_id, organization_id)
        if item.recommended_price is None:
            raise AppError(
                "Não há preço recomendado para decisão.",
                status_code=400,
                code="NO_RECOMMENDATION",
            )
        now = datetime.now(UTC)
        required = int(data.get("required_approvals", 1))
        decision = PricingDecision(
            id=uuid.uuid4(),
            organization_id=organization_id,
            recommendation_item_id=item.id,
            status=DecisionStatus.DRAFT,
            selected_scenario=data.get("selected_scenario")
            or (item.result_snapshot or {}).get("selected_scenario"),
            recommended_price=item.recommended_price,
            decision_reason=data.get("decision_reason"),
            expires_at=_parse_dt(data.get("expires_at")),
            created_by=user_id,
            created_at=now,
        )
        self.db.add(decision)
        await self.db.flush()
        for level in range(1, required + 1):
            self.db.add(
                PricingDecisionApproval(
                    id=uuid.uuid4(),
                    pricing_decision_id=decision.id,
                    approval_level=level,
                    status="PENDING",
                    created_at=now,
                )
            )
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_decision",
                entity_id=decision.id,
                action="CREATE",
            )
        return decision

    async def get_decision(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID
    ) -> PricingDecision:
        result = await self.db.execute(
            select(PricingDecision).where(
                PricingDecision.id == decision_id,
                PricingDecision.organization_id == organization_id,
            )
        )
        d = result.scalar_one_or_none()
        if not d:
            raise AppError("Decisão não encontrada.", status_code=404, code="NOT_FOUND")
        return d

    async def list_decisions(
        self, organization_id: uuid.UUID, *, status: str | None = None
    ) -> list[PricingDecision]:
        q = select(PricingDecision).where(PricingDecision.organization_id == organization_id)
        if status:
            q = q.where(PricingDecision.status == status)
        q = q.order_by(PricingDecision.created_at.desc()).limit(200)
        return list((await self.db.execute(q)).scalars().all())

    async def submit_decision(
        self,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecision:
        d = await self.get_decision(decision_id, organization_id)
        if d.status not in (DecisionStatus.DRAFT, DecisionStatus.GENERATED, DecisionStatus.REVIEW_REQUIRED):
            raise AppError("Status inválido para submissão.", status_code=400, code="INVALID_STATUS")
        d.status = DecisionStatus.PENDING_APPROVAL
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="pricing_decision", entity_id=d.id, action="SUBMIT"
            )
        return d

    async def approve_decision(
        self,
        *,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: str | None = None,
        approved_price: Decimal | None = None,
        allow_self_approval: bool = False,
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecision:
        d = await self.get_decision(decision_id, organization_id)
        if d.status != DecisionStatus.PENDING_APPROVAL:
            raise AppError("Decisão não está pendente de aprovação.", status_code=400, code="INVALID_STATUS")
        if d.expires_at and d.expires_at < datetime.now(UTC):
            d.status = DecisionStatus.EXPIRED
            await self.db.flush()
            raise AppError("Decisão expirada.", status_code=400, code="EXPIRED")
        if not allow_self_approval and d.created_by and d.created_by == user_id:
            raise AppError(
                "Autoaprovação bloqueada pela política.",
                status_code=403,
                code="SELF_APPROVAL_BLOCKED",
            )

        approvals = list(
            (
                await self.db.execute(
                    select(PricingDecisionApproval)
                    .where(PricingDecisionApproval.pricing_decision_id == d.id)
                    .order_by(PricingDecisionApproval.approval_level)
                )
            ).scalars().all()
        )
        pending = next((a for a in approvals if a.status == "PENDING"), None)
        if not pending:
            raise AppError("Nenhuma aprovação pendente.", status_code=400, code="NO_PENDING_APPROVAL")

        # bloqueia mesmo usuário em níveis diferentes
        prior_approvers = {a.decided_by for a in approvals if a.decision == "APPROVED" and a.decided_by}
        if user_id in prior_approvers:
            raise AppError(
                "Mesmo usuário não pode aprovar múltiplos níveis.",
                status_code=403,
                code="DUPLICATE_APPROVER",
            )

        now = datetime.now(UTC)
        pending.status = "APPROVED"
        pending.decision = "APPROVED"
        pending.comment = comment
        pending.decided_by = user_id
        pending.decided_at = now

        still_pending = [a for a in approvals if a.id != pending.id and a.status == "PENDING"]
        if still_pending:
            await self.db.flush()
            if audit_ctx:
                await self.audit.log(
                    ctx=audit_ctx,
                    entity_type="pricing_decision",
                    entity_id=d.id,
                    action="APPROVE_PARTIAL",
                    after_data={"level": pending.approval_level},
                )
            return d

        d.status = DecisionStatus.APPROVED_PENDING_IMPLEMENTATION
        d.approved_price = approved_price or d.recommended_price
        d.approved_at = now
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_decision",
                entity_id=d.id,
                action="APPROVE",
                after_data={"approved_price": str(d.approved_price)},
            )
        return d

    async def reject_decision(
        self,
        *,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: str | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecision:
        d = await self.get_decision(decision_id, organization_id)
        if d.status != DecisionStatus.PENDING_APPROVAL:
            raise AppError("Decisão não está pendente.", status_code=400, code="INVALID_STATUS")
        now = datetime.now(UTC)
        approvals = list(
            (
                await self.db.execute(
                    select(PricingDecisionApproval).where(
                        PricingDecisionApproval.pricing_decision_id == d.id,
                        PricingDecisionApproval.status == "PENDING",
                    )
                )
            ).scalars().all()
        )
        for a in approvals:
            a.status = "REJECTED"
            a.decision = "REJECTED"
            a.comment = comment
            a.decided_by = user_id
            a.decided_at = now
        d.status = DecisionStatus.REJECTED
        d.rejected_at = now
        d.decision_reason = comment or d.decision_reason
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="pricing_decision", entity_id=d.id, action="REJECT"
            )
        return d

    async def cancel_decision(
        self,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecision:
        d = await self.get_decision(decision_id, organization_id)
        if d.status in (
            DecisionStatus.IMPLEMENTED_MATCHED,
            DecisionStatus.IMPLEMENTED_DIFFERENT,
        ):
            raise AppError("Não é possível cancelar decisão já implantada.", status_code=400, code="INVALID_STATUS")
        d.status = DecisionStatus.CANCELLED
        d.cancelled_at = datetime.now(UTC)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx, entity_type="pricing_decision", entity_id=d.id, action="CANCEL"
            )
        return d

    async def add_evidence(
        self,
        *,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        data: dict[str, Any],
        audit_ctx: AuditContext | None = None,
    ) -> PricingDecisionEvidence:
        await self.get_decision(decision_id, organization_id)
        ev = PricingDecisionEvidence(
            id=uuid.uuid4(),
            pricing_decision_id=decision_id,
            evidence_type=data.get("evidence_type", "NOTE"),
            description=data.get("description"),
            storage_key=data.get("storage_key"),
            sha256=data.get("sha256"),
            content_type=data.get("content_type"),
            size_bytes=data.get("size_bytes"),
            original_filename=data.get("original_filename"),
            structured_payload=data.get("structured_payload"),
            uploaded_by=user_id,
            uploaded_at=datetime.now(UTC),
        )
        self.db.add(ev)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_decision_evidence",
                entity_id=ev.id,
                action="ADD_EVIDENCE",
            )
        return ev

    async def list_evidence(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[PricingDecisionEvidence]:
        await self.get_decision(decision_id, organization_id)
        result = await self.db.execute(
            select(PricingDecisionEvidence).where(
                PricingDecisionEvidence.pricing_decision_id == decision_id
            )
        )
        return list(result.scalars().all())

    async def confirm_implementation(
        self,
        *,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        implemented_price: Decimal,
        implemented_at: datetime | None = None,
        note: str | None = None,
        tolerance: Decimal | None = None,
        audit_ctx: AuditContext | None = None,
    ) -> PricingImplementationCheck:
        d = await self.get_decision(decision_id, organization_id)
        if d.approved_price is None or d.status not in (
            DecisionStatus.APPROVED,
            DecisionStatus.APPROVED_PENDING_IMPLEMENTATION,
            DecisionStatus.IMPLEMENTATION_NOT_CONFIRMED,
        ):
            raise AppError(
                "Decisão precisa estar aprovada para confirmar implantação.",
                status_code=400,
                code="INVALID_STATUS",
            )
        tol = tolerance or Decimal("0.01")
        variance = implemented_price - d.approved_price
        if abs(variance) <= tol:
            status = "MATCHED" if variance == _ZERO else "WITHIN_TOLERANCE"
            d.status = DecisionStatus.IMPLEMENTED_MATCHED
        else:
            status = "DIFFERENT"
            d.status = DecisionStatus.IMPLEMENTED_DIFFERENT

        now = datetime.now(UTC)
        check = PricingImplementationCheck(
            id=uuid.uuid4(),
            pricing_decision_id=d.id,
            check_type="MANUAL",
            status=status,
            approved_price=d.approved_price,
            implemented_price=implemented_price,
            implementation_variance=variance,
            implemented_at=implemented_at or now,
            checked_at=now,
            details={"note": note, "xpert_write": False},
            checked_by=user_id,
            created_at=now,
        )
        self.db.add(check)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_implementation_check",
                entity_id=check.id,
                action="CONFIRM_IMPLEMENTATION",
                after_data={"status": status, "variance": str(variance)},
            )
        return check

    async def check_erp_price(
        self,
        *,
        decision_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        implemented_price: Decimal | None = None,
        price_snapshot_id: uuid.UUID | None = None,
        tolerance: Decimal | None = None,
        stale: bool = False,
        audit_ctx: AuditContext | None = None,
    ) -> PricingImplementationCheck:
        """Compara preço aprovado com snapshot ERP ou valor informado. Sem escrita no XPERT."""
        d = await self.get_decision(decision_id, organization_id)
        if d.approved_price is None:
            raise AppError("Sem preço aprovado.", status_code=400, code="NO_APPROVED_PRICE")
        now = datetime.now(UTC)
        tol = tolerance or Decimal("0.01")

        if stale:
            status = "STALE_PRICE_SNAPSHOT"
            impl = None
            variance = None
        elif implemented_price is None:
            status = "NOT_FOUND"
            impl = None
            variance = None
        else:
            variance = implemented_price - d.approved_price
            if abs(variance) <= tol:
                status = "MATCHED" if variance == _ZERO else "WITHIN_TOLERANCE"
                d.status = DecisionStatus.IMPLEMENTED_MATCHED
            else:
                status = "DIFFERENT"
                d.status = DecisionStatus.IMPLEMENTED_DIFFERENT
            impl = implemented_price

        check = PricingImplementationCheck(
            id=uuid.uuid4(),
            pricing_decision_id=d.id,
            check_type="ERP_SNAPSHOT",
            status=status,
            approved_price=d.approved_price,
            implemented_price=impl,
            implementation_variance=variance,
            price_snapshot_id=price_snapshot_id,
            checked_at=now,
            details={"xpert_write": False},
            checked_by=user_id,
            created_at=now,
        )
        self.db.add(check)
        await self.db.flush()
        if audit_ctx:
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="pricing_implementation_check",
                entity_id=check.id,
                action="CHECK_ERP_PRICE",
                after_data={"status": status},
            )
        return check

    async def list_implementation_checks(
        self, decision_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[PricingImplementationCheck]:
        await self.get_decision(decision_id, organization_id)
        result = await self.db.execute(
            select(PricingImplementationCheck)
            .where(PricingImplementationCheck.pricing_decision_id == decision_id)
            .order_by(PricingImplementationCheck.created_at.desc())
        )
        return list(result.scalars().all())

    async def summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        items = await self.list_items(organization_id)
        decisions = await self.list_decisions(organization_id)
        below_floor = sum(
            1
            for i in items
            if i.commercial_floor_price is not None
            and i.current_price is not None
            and i.current_price < i.commercial_floor_price
        )
        margins = [
            i.current_margin_per_liter
            for i in items
            if i.current_margin_per_liter is not None
        ]
        avg_margin = (sum(margins) / len(margins)) if margins else None
        return {
            "monitored_products": len({(i.station_id, i.canonical_product_id) for i in items}),
            "below_floor": below_floor,
            "average_margin_per_liter": str(avg_margin) if avg_margin is not None else None,
            "increase_recommendations": sum(
                1 for i in items if i.recommendation_status == RecommendationStatus.INCREASE
            ),
            "decrease_recommendations": sum(
                1 for i in items if i.recommendation_status == RecommendationStatus.DECREASE
            ),
            "pending_approval": sum(
                1 for d in decisions if d.status == DecisionStatus.PENDING_APPROVAL
            ),
            "approved_not_implemented": sum(
                1
                for d in decisions
                if d.status == DecisionStatus.APPROVED_PENDING_IMPLEMENTATION
            ),
            "divergent_implementations": sum(
                1 for d in decisions if d.status == DecisionStatus.IMPLEMENTED_DIFFERENT
            ),
            "disclaimer": DISCLAIMER,
            "xpert_write_enabled": False,
        }

    async def create_synthetic_homologation_pack(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        station_id: uuid.UUID,
        product_id: uuid.UUID,
        audit_ctx: AuditContext | None = None,
    ) -> dict[str, Any]:
        """Gera cenários sintéticos de homologação sem tocar XPERT."""
        base_policy = {
            "name": "Synthetic homologation policy",
            "cost_basis_type": CostBasisType.SYNTHETIC_COST,
            "minimum_margin_per_liter": "0.30",
            "target_margin_per_liter": "0.50",
            "maximum_increase_per_liter": "0.20",
            "maximum_decrease_per_liter": "0.20",
            "minimum_change_per_liter": "0.02",
            "rounding_policy": "NEAREST_CENT",
            "default_scenario": PricingScenarioType.BALANCED,
            "required_approvals": 1,
            "allow_self_approval": False,
        }
        scenarios = [
            {
                "label": "below_floor",
                "synthetic_cost": {"cost_per_liter": "5.00", "cost_confidence": "HIGH"},
                "synthetic_price": {"current_price": "5.10"},
            },
            {
                "label": "at_target",
                "synthetic_cost": {"cost_per_liter": "5.00", "cost_confidence": "HIGH"},
                "synthetic_price": {"current_price": "5.50"},
            },
            {
                "label": "missing_cost",
                "synthetic_cost": {"cost_per_liter": None},
                "synthetic_price": {"current_price": "5.50"},
            },
            {
                "label": "missing_price",
                "synthetic_cost": {"cost_per_liter": "5.00"},
                "synthetic_price": {"current_price": None},
            },
            {
                "label": "replacement_up",
                "synthetic_cost": {
                    "cost_per_liter": "5.00",
                    "replacement_cost": "5.40",
                    "cost_confidence": "HIGH",
                },
                "synthetic_price": {"current_price": "5.60"},
            },
            {
                "label": "guardrail_increase",
                "synthetic_cost": {"cost_per_liter": "5.00"},
                "synthetic_price": {"current_price": "5.10"},
                "synthetic_policy": {
                    **base_policy,
                    "target_margin_per_liter": "1.00",
                    "maximum_increase_per_liter": "0.05",
                },
            },
            {
                "label": "hindsight_blocked",
                "synthetic_cost": {
                    "cost_per_liter": "5.00",
                    "cost_available_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                },
                "synthetic_price": {"current_price": "5.50"},
            },
        ]
        runs = []
        for sc in scenarios:
            data = {
                "trigger_type": "SYNTHETIC",
                "station_id": station_id,
                "canonical_product_id": product_id,
                "price_type": "POSTED_PRICE",
                "synthetic_policy": sc.get("synthetic_policy") or base_policy,
                "items": [
                    {
                        "station_id": station_id,
                        "canonical_product_id": product_id,
                        "synthetic_cost": sc["synthetic_cost"],
                        "synthetic_price": sc["synthetic_price"],
                        "synthetic_policy": sc.get("synthetic_policy") or base_policy,
                        "reference_daily_volume": "1000",
                    }
                ],
            }
            run = await self.run_recommendations(
                organization_id=organization_id,
                user_id=user_id,
                data=data,
                audit_ctx=audit_ctx,
            )
            runs.append({"label": sc["label"], "run_id": str(run.id), "status": run.status})
        return {"scenarios": runs, "disclaimer": DISCLAIMER, "xpert_write": False}
