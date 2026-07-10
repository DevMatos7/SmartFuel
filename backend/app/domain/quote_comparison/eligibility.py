from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.quote_comparison_enums import EligibilityStatus, ReasonSeverity


@dataclass
class EligibilityReason:
    code: str
    severity: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


REASON_MESSAGES: dict[str, str] = {
    "QUOTE_NOT_KNOWN_AT_COMPARISON_TIME": "A cotação ainda não era conhecida na data da comparação.",
    "QUOTE_NOT_ACTIVE_AT_COMPARISON_TIME": "A cotação não estava ativa na data da comparação.",
    "QUOTE_EXPIRED": "A cotação já estava vencida na data da comparação.",
    "ITEM_EXPIRED": "O item já estava vencido na data da comparação.",
    "STATION_NOT_ALLOWED": "O posto informado não corresponde à cotação.",
    "SUPPLIER_NOT_ALLOWED": "A distribuidora não é permitida para este posto e produto.",
    "PRODUCT_NOT_ALLOWED": "O produto não é permitido para esta comparação.",
    "BASE_NOT_ALLOWED": "A base de distribuição não é permitida para esta proposta.",
    "MINIMUM_VOLUME_NOT_REACHED": "O volume solicitado é inferior ao mínimo da proposta.",
    "AVAILABLE_VOLUME_INSUFFICIENT": "O volume disponível é inferior ao volume solicitado.",
    "AVAILABLE_VOLUME_NOT_INFORMED": "O volume disponível não foi informado.",
    "DELIVERY_AFTER_REQUIRED_DATE": "A entrega prevista é posterior à data necessária.",
    "DELIVERY_DATE_NOT_INFORMED": "A data de entrega não foi informada.",
    "MISSING_PAYMENT_TERM": "A condição de pagamento não está disponível.",
    "MISSING_FINANCIAL_PARAMETER": "Não há parâmetro financeiro vigente para calcular o custo equivalente.",
    "INVALID_FINANCIAL_PARAMETER": "O parâmetro financeiro vigente é inválido.",
    "INVALID_DELIVERED_COST": "O custo entregue calculado é inválido.",
    "CROSS_ORGANIZATION_REFERENCE": "Referência fora da organização.",
    "SUPPLIER_RULE_NOT_EXPLICIT": "Não há regra explícita de fornecimento para esta combinação.",
    "QUOTE_NEAR_EXPIRATION": "A proposta está próxima do vencimento.",
    "LOW_AVAILABLE_MARGIN": "O volume disponível está muito próximo do solicitado.",
}


def make_reason(
    code: str,
    *,
    severity: ReasonSeverity | str,
    metadata: dict[str, Any] | None = None,
    message: str | None = None,
) -> EligibilityReason:
    return EligibilityReason(
        code=code,
        severity=str(severity),
        message=message or REASON_MESSAGES.get(code, code),
        metadata=metadata or {},
    )


def resolve_eligibility_status(reasons: list[EligibilityReason]) -> str:
    if any(r.severity in {ReasonSeverity.BLOCKING, ReasonSeverity.BLOCKING.value} for r in reasons):
        return EligibilityStatus.INELIGIBLE
    if any(r.severity in {ReasonSeverity.WARNING, ReasonSeverity.WARNING.value} for r in reasons):
        return EligibilityStatus.ELIGIBLE_WITH_WARNINGS
    return EligibilityStatus.ELIGIBLE
