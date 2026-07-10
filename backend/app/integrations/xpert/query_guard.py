from __future__ import annotations

from app.core.xpert_sync_enums import ErpContractStatus
from app.integrations.xpert.canonical_hash import query_file_hash
from app.integrations.xpert.secret_resolver import load_query_file
from app.models.erp_integration import ErpDataset


class QueryChangedError(Exception):
    code = "QUERY_CHANGED_AFTER_VALIDATION"


def current_query_hash(query_file: str) -> str:
    return query_file_hash(load_query_file(query_file))


def sync_dataset_query_hash(dataset: ErpDataset) -> str:
    current = current_query_hash(dataset.query_file)
    dataset.query_hash = current
    return current


def ensure_dataset_query_unchanged(dataset: ErpDataset) -> None:
    current = current_query_hash(dataset.query_file)
    if dataset.query_hash and dataset.query_hash != current:
        dataset.contract_status = ErpContractStatus.PENDING_VALIDATION
        dataset.schedule_enabled = False
        dataset.enabled = False
        raise QueryChangedError("A consulta foi alterada após a validação do contrato.")
