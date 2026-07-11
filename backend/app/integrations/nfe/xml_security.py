"""Parser e validação segura de XML de NF-e (bloqueio XXE)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from xml.etree import ElementTree as ET

from defusedxml.ElementTree import fromstring as safe_fromstring

from app.core.exceptions import AppError

_ACCESS_KEY_RE = re.compile(r"^\d{44}$")
_MAX_XML_BYTES = 5 * 1024 * 1024  # 5 MiB


@dataclass(frozen=True)
class ParsedNfeHeader:
    access_key: str
    issuer_cnpj: str
    recipient_cnpj: str
    document_number: str
    series: str
    issue_datetime: str | None
    total_amount: Decimal | None
    item_count: int


def validate_access_key(access_key: str | None) -> str:
    key = (access_key or "").strip()
    if not _ACCESS_KEY_RE.match(key):
        raise AppError(
            "Chave de acesso da NF-e inválida.",
            status_code=400,
            code="INVALID_ACCESS_KEY",
        )
    return key


def xml_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ensure_xml_size(content: bytes) -> None:
    if len(content) > _MAX_XML_BYTES:
        raise AppError(
            "XML excede o tamanho máximo permitido.",
            status_code=400,
            code="XML_TOO_LARGE",
        )
    if not content:
        raise AppError("XML vazio.", status_code=400, code="XML_EMPTY")


def parse_nfe_xml(content: bytes) -> tuple[ParsedNfeHeader | None, list[dict[str, Any]]]:
    """Parse seguro (defusedxml). Retorna (header, erros)."""
    ensure_xml_size(content)
    errors: list[dict[str, Any]] = []
    try:
        root = safe_fromstring(content)
    except ET.ParseError as exc:
        return None, [{"code": "XML_PARSE_ERROR", "message": str(exc)}]
    except Exception as exc:  # noqa: BLE001 — falha de segurança/parse
        return None, [{"code": "XML_PARSE_ERROR", "message": str(exc)}]

    def _text(path: str) -> str | None:
        node = root.find(path)
        if node is None:
            # namespaces comuns da NF-e
            for el in root.iter():
                tag = el.tag.rsplit("}", 1)[-1]
                wanted = path.rsplit("/", 1)[-1]
                if tag == wanted and el.text:
                    return el.text.strip()
            return None
        return (node.text or "").strip() or None

    # Extração tolerante a namespaces
    texts: dict[str, str | None] = {}
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag in {
            "chNFe",
            "CNPJ",
            "nNF",
            "serie",
            "dhEmi",
            "dEmi",
            "vNF",
        } and tag not in texts and el.text:
            texts[tag] = el.text.strip()

    access_key = texts.get("chNFe")
    # CNPJ emitente/destinatário: primeira e segunda ocorrência típicas
    cnpjs = [
        el.text.strip()
        for el in root.iter()
        if el.tag.rsplit("}", 1)[-1] == "CNPJ" and el.text
    ]
    issuer = cnpjs[0] if cnpjs else None
    recipient = cnpjs[1] if len(cnpjs) > 1 else (cnpjs[0] if cnpjs else None)

    item_count = sum(1 for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "det")

    if not access_key:
        # InfCpl / protNFe às vezes trazem a chave
        for el in root.iter():
            if el.tag.rsplit("}", 1)[-1] == "chNFe" and el.text:
                access_key = el.text.strip()
                break

    try:
        if access_key:
            access_key = validate_access_key(access_key)
    except AppError as exc:
        errors.append({"code": exc.code, "message": str(exc)})
        access_key = access_key or ""

    total_raw = texts.get("vNF")
    total_amount = Decimal(total_raw) if total_raw else None

    if not access_key or not issuer or not recipient:
        errors.append({"code": "XML_MISSING_REQUIRED_FIELDS", "message": "Campos obrigatórios ausentes no XML."})
        if not access_key:
            return None, errors

    header = ParsedNfeHeader(
        access_key=access_key,
        issuer_cnpj=(issuer or "").zfill(14)[:14],
        recipient_cnpj=(recipient or "").zfill(14)[:14],
        document_number=texts.get("nNF") or "",
        series=texts.get("serie") or "",
        issue_datetime=texts.get("dhEmi") or texts.get("dEmi"),
        total_amount=total_amount,
        item_count=item_count,
    )
    return header, errors
