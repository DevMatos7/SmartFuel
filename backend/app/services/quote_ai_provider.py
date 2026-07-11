"""Provedores de extração estruturada de cotações (Sprint 13).

A IA apenas extrai e sugere. Sem ferramentas de rede, escrita ou ativação.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.quote_ai_enums import PROMPT_INJECTION_PATTERNS, QuoteAiQualityCode


@dataclass
class ExtractionResult:
    document_type: str
    structured_output: dict[str, Any]
    document_confidence: Decimal
    warnings: list[str] = field(default_factory=list)
    unparsed_fragments: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    provider_cost: Decimal = Decimal("0")
    cost_currency: str = "USD"
    provider: str = "mock"
    model: str = "mock-extractor-v1"
    prompt_version: str = "v1"
    schema_version: str = "v1"
    raw_provider_response: dict[str, Any] | None = None


class QuoteExtractionProvider(ABC):
    @abstractmethod
    async def extract(self, *, raw_text: str, document_type: str | None = None) -> ExtractionResult:
        raise NotImplementedError


def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(p in lowered for p in PROMPT_INJECTION_PATTERNS)


def _parse_brl(value: str) -> str | None:
    cleaned = value.strip().replace("R$", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    return format(amount.quantize(Decimal("0.0001")), "f")


_PRODUCT_LINE = re.compile(
    r"(?P<name>gasolina(?:\s+comum)?|etanol|diesel\s*s[\s\-]?10|diesel\s*s[\s\-]?500|s10)"
    r"\s*[:\-]?\s*(?:R\$\s*)?(?P<price>\d+[.,]\d{2,4})",
    re.IGNORECASE,
)
_BASE = re.compile(r"base\s+([A-Za-zÀ-ÿ\s]+)", re.IGNORECASE)
_DISTRIBUTOR = re.compile(
    r"(distribuidora\s+[A-Za-zÀ-ÿ0-9\s&\.\-]+)|(?:^|\n)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9\s&\.\-]{2,40})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PAYMENT_DAYS = re.compile(r"(?:pagamento|pagto)?\s*(\d+)\s*dias?", re.IGNORECASE)
_MIN_VOLUME = re.compile(r"(?:pedido\s+m[ií]nimo|m[ií]nimo|volume)\s*[:=]?\s*([\d\.]+)\s*(?:l|litros)?", re.IGNORECASE)
_VALID_UNTIL_HOUR = re.compile(r"v[aá]lido\s+at[eé]\s+(\d{1,2})h", re.IGNORECASE)
_VALID_DURATION = re.compile(r"v[aá]lido\s+por\s+(\d+)\s*horas?", re.IGNORECASE)


class MockQuoteExtractionProvider(QuoteExtractionProvider):
    """Parser determinístico para homologação sintética — sem inventar campos ausentes."""

    async def extract(self, *, raw_text: str, document_type: str | None = None) -> ExtractionResult:
        warnings: list[str] = []
        if detect_prompt_injection(raw_text):
            warnings.append(QuoteAiQualityCode.PROMPT_INJECTION_CONTENT_DETECTED)

        items: list[dict[str, Any]] = []
        for match in _PRODUCT_LINE.finditer(raw_text):
            price = _parse_brl(match.group("price"))
            if price is None:
                continue
            name = re.sub(r"\s+", " ", match.group("name")).strip()
            items.append(
                {
                    "raw_product_name": name,
                    "price_per_liter": price,
                    "currency": "BRL",
                    "minimum_volume_liters": None,
                    "payment_terms": [],
                    "freight": {"type": None, "amount": None},
                    "confidence": 0.94,
                    "evidence": match.group(0),
                }
            )

        vol = _MIN_VOLUME.search(raw_text)
        min_vol = None
        if vol:
            try:
                min_vol = str(Decimal(vol.group(1).replace(".", "")))
            except InvalidOperation:
                min_vol = None
        pay = _PAYMENT_DAYS.search(raw_text)
        payment_days = int(pay.group(1)) if pay else None
        for item in items:
            if min_vol:
                item["minimum_volume_liters"] = min_vol
            if payment_days is not None:
                item["payment_terms"] = [
                    {
                        "raw_text": f"{payment_days} dias",
                        "days": payment_days,
                        "price_per_liter": item["price_per_liter"],
                    }
                ]

        base_match = _BASE.search(raw_text)
        base_name = base_match.group(1).strip() if base_match else None

        distributor_name = None
        for line in raw_text.splitlines():
            line = line.strip()
            if line.lower().startswith("distribuidora"):
                distributor_name = line
                break

        valid_until = None
        value_origin_valid = "EXTRACTED"
        hour = _VALID_UNTIL_HOUR.search(raw_text)
        duration = _VALID_DURATION.search(raw_text)
        if hour:
            valid_until = {"raw": hour.group(0), "hour": int(hour.group(1)), "origin": "EXTRACTED"}
        elif duration:
            valid_until = {
                "raw": duration.group(0),
                "hours": int(duration.group(1)),
                "origin": "DERIVED_FROM_EXPLICIT_DURATION",
            }
            value_origin_valid = "DERIVED"

        confidences = [Decimal(str(i["confidence"])) for i in items] or [Decimal("0")]
        price_conf = min(confidences)
        if not items:
            warnings.append("NO_ITEMS_EXTRACTED")
            document_confidence = Decimal("0.20")
        else:
            document_confidence = (price_conf + Decimal("0.85")) / 2

        structured = {
            "document_type": document_type or ("QUOTE_MESSAGE" if items else "UNKNOWN_DOCUMENT"),
            "distributor": {
                "raw_name": distributor_name,
                "cnpj": None,
                "confidence": 0.9 if distributor_name else None,
                "evidence": distributor_name,
            },
            "base": {
                "raw_name": base_name,
                "confidence": 0.88 if base_name else None,
            },
            "quote_datetime": None,
            "valid_until": valid_until,
            "valid_until_origin": value_origin_valid if valid_until else None,
            "items": items,
            "warnings": warnings,
            "unparsed_fragments": [],
        }

        tokens_in = max(1, len(raw_text) // 4)
        tokens_out = max(1, len(str(structured)) // 4)
        return ExtractionResult(
            document_type=structured["document_type"],
            structured_output=structured,
            document_confidence=document_confidence.quantize(Decimal("0.000001")),
            warnings=warnings,
            unparsed_fragments=[],
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            provider_cost=Decimal("0"),
            provider="mock",
            model="mock-extractor-v1",
            raw_provider_response={"mode": "deterministic_mock"},
        )


class OpenAIQuoteExtractionProvider(QuoteExtractionProvider):
    """Stub — requer secret_ref e flag habilitada. Não inventa campos."""

    def __init__(self, *, model: str, secret_ref: str | None) -> None:
        self.model = model
        self.secret_ref = secret_ref

    async def extract(self, *, raw_text: str, document_type: str | None = None) -> ExtractionResult:
        raise NotImplementedError(
            "OpenAIQuoteExtractionProvider requer configuração homologada de secret_ref."
        )


def get_quote_extraction_provider(
    *, provider: str = "mock", model: str = "mock-extractor-v1", secret_ref: str | None = None
) -> QuoteExtractionProvider:
    if provider == "mock":
        return MockQuoteExtractionProvider()
    if provider == "openai":
        return OpenAIQuoteExtractionProvider(model=model, secret_ref=secret_ref)
    return MockQuoteExtractionProvider()
