from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.exceptions import AppError
from app.core.permissions import Permission
from app.schemas.fuel_purchases_analytics import (
    AccountsPayableAgingBucket,
    AccountsPayableSummaryResponse,
    AccountsPayableTitleListRow,
    FuelPurchaseInvoiceDetail,
    FuelPurchaseInvoiceItemRow,
    FuelPurchaseInvoiceListRow,
    FuelPurchaseInvoiceTitleRow,
    FuelPurchaseInvoiceXmlInfo,
    FuelPurchasesByDistributorRow,
    FuelPurchasesByProductRow,
    FuelPurchasesByStationRow,
    FuelPurchasesCostsResponse,
    FuelPurchasesDataQualityResponse,
    FuelPurchasesFreshnessResponse,
    FuelPurchasesSummaryResponse,
    FuelPurchasesTrendPoint,
    NfeDocumentDetail,
    NfeDocumentRow,
    PaginatedInvoices,
    PaginatedNfeDocuments,
    PaginatedTitles,
)
from app.services.auth_service import AuthService, AuthenticatedUser
from app.services.fuel_purchases_analytics_service import FuelPurchasesAnalyticsService

analytics_router = APIRouter(prefix="/analytics/fuel-purchases", tags=["fuel-purchases-analytics"])
invoices_router = APIRouter(prefix="/fuel-purchase-invoices", tags=["fuel-purchase-invoices"])
ap_router = APIRouter(prefix="/accounts-payable", tags=["accounts-payable"])
nfe_router = APIRouter(prefix="/nfe-documents", tags=["nfe-documents"])


def _ensure(user: AuthenticatedUser, permission: Permission) -> None:
    if permission.value not in user.permissions:
        raise AppError("Você não possui permissão para executar esta ação.", status_code=403, code="FORBIDDEN")


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


async def _resolve_station_ids(
    auth: AuthService,
    user: AuthenticatedUser,
    station_ids: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    allowed = await auth.allowed_stations(user)
    allowed_ids = {s.id for s in allowed}
    if user.has_all_stations_access:
        if station_ids:
            return station_ids
        return [s.id for s in allowed]
    if station_ids:
        for sid in station_ids:
            if sid not in allowed_ids:
                raise AppError("Posto fora do escopo.", status_code=403, code="FORBIDDEN")
        return station_ids
    return list(allowed_ids)


@analytics_router.get("/summary", response_model=FuelPurchasesSummaryResponse)
async def purchases_summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchasesSummaryResponse:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    include_cost = Permission.FUEL_PURCHASES_VIEW_COST.value in user.permissions
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    data = await FuelPurchasesAnalyticsService(db).summary(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
        include_cost=include_cost,
    )
    return FuelPurchasesSummaryResponse(
        purchased_volume_liters=_dec(data["purchased_volume_liters"]) or "0",
        gross_purchase_amount=_dec(data["gross_purchase_amount"]) or "0",
        commercial_delivered_cost=(_dec(data["commercial_delivered_cost"]) or "0") if include_cost else "0",
        average_delivered_cost_per_liter=_dec(data.get("average_delivered_cost_per_liter")),
        total_freight_amount=_dec(data["total_freight_amount"]) or "0",
        total_discount_amount=_dec(data["total_discount_amount"]) or "0",
        invoice_count=data["invoice_count"],
        weighted_term_days=_dec(data.get("weighted_term_days")),
        open_payable_amount=_dec(data.get("open_payable_amount")),
        erp_recorded_cost=_dec(data.get("erp_recorded_cost")),
    )


@analytics_router.get("/trend", response_model=list[FuelPurchasesTrendPoint])
async def purchases_trend(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchasesTrendPoint]:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    rows = await FuelPurchasesAnalyticsService(db).trend(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        FuelPurchasesTrendPoint(
            business_date=r["business_date"],
            purchased_volume_liters=_dec(r["purchased_volume_liters"]) or "0",
            gross_purchase_amount=_dec(r["gross_purchase_amount"]) or "0",
            commercial_delivered_cost=_dec(r["commercial_delivered_cost"]) or "0",
            average_delivered_cost_per_liter=_dec(r.get("average_delivered_cost_per_liter")),
            freight_amount=_dec(r["freight_amount"]) or "0",
        )
        for r in rows
    ]


@analytics_router.get("/by-product", response_model=list[FuelPurchasesByProductRow])
async def purchases_by_product(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchasesByProductRow]:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    rows = await FuelPurchasesAnalyticsService(db).by_product(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        FuelPurchasesByProductRow(
            product_id=r["product_id"],
            product_name=r["product_name"],
            purchased_volume_liters=_dec(r["purchased_volume_liters"]) or "0",
            gross_purchase_amount=_dec(r["gross_purchase_amount"]) or "0",
            commercial_delivered_cost=_dec(r["commercial_delivered_cost"]) or "0",
            average_delivered_cost_per_liter=_dec(r.get("average_delivered_cost_per_liter")),
        )
        for r in rows
    ]


@analytics_router.get("/by-station", response_model=list[FuelPurchasesByStationRow])
async def purchases_by_station(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchasesByStationRow]:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    rows = await FuelPurchasesAnalyticsService(db).by_station(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        FuelPurchasesByStationRow(
            station_id=r["station_id"],
            station_name=r["station_name"],
            purchased_volume_liters=_dec(r["purchased_volume_liters"]) or "0",
            gross_purchase_amount=_dec(r["gross_purchase_amount"]) or "0",
            commercial_delivered_cost=_dec(r["commercial_delivered_cost"]) or "0",
            invoice_count=r["invoice_count"],
        )
        for r in rows
    ]


@analytics_router.get("/by-distributor", response_model=list[FuelPurchasesByDistributorRow])
async def purchases_by_distributor(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchasesByDistributorRow]:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    rows = await FuelPurchasesAnalyticsService(db).by_distributor(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return [
        FuelPurchasesByDistributorRow(
            distributor_id=r["distributor_id"],
            distributor_name=r["distributor_name"],
            purchased_volume_liters=_dec(r["purchased_volume_liters"]) or "0",
            gross_purchase_amount=_dec(r["gross_purchase_amount"]) or "0",
            commercial_delivered_cost=_dec(r["commercial_delivered_cost"]) or "0",
            average_delivered_cost_per_liter=_dec(r.get("average_delivered_cost_per_liter")),
            invoice_count=r["invoice_count"],
        )
        for r in rows
    ]


@analytics_router.get("/costs", response_model=FuelPurchasesCostsResponse)
async def purchases_costs(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchasesCostsResponse:
    _ensure(user, Permission.FUEL_PURCHASES_VIEW_COST)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    data = await FuelPurchasesAnalyticsService(db).costs(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return FuelPurchasesCostsResponse(
        purchased_volume_liters=_dec(data["purchased_volume_liters"]) or "0",
        gross_purchase_amount=_dec(data["gross_purchase_amount"]) or "0",
        discount_amount=_dec(data["discount_amount"]) or "0",
        freight_amount=_dec(data["freight_amount"]) or "0",
        insurance_amount=_dec(data["insurance_amount"]) or "0",
        other_expenses_amount=_dec(data["other_expenses_amount"]) or "0",
        commercial_delivered_cost=_dec(data["commercial_delivered_cost"]) or "0",
        erp_recorded_cost=_dec(data.get("erp_recorded_cost")),
        average_delivered_cost_per_liter=_dec(data.get("average_delivered_cost_per_liter")),
        invoice_count=data["invoice_count"],
        item_count=data["item_count"],
    )


@analytics_router.get("/data-quality", response_model=FuelPurchasesDataQualityResponse)
async def purchases_data_quality(
    date_from: date = Query(...),
    date_to: date = Query(...),
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchasesDataQualityResponse:
    _ensure(user, Permission.PURCHASE_DATA_QUALITY_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    data = await FuelPurchasesAnalyticsService(db).data_quality(
        organization_id=user.organization_id,
        station_ids=stations,
        date_from=date_from,
        date_to=date_to,
    )
    return FuelPurchasesDataQualityResponse(
        unmapped_item_count=data["unmapped_item_count"],
        unmapped_volume_liters=_dec(data["unmapped_volume_liters"]) or "0",
        unmapped_supplier_count=data["unmapped_supplier_count"],
        missing_cost_item_count=data["missing_cost_item_count"],
        missing_xml_count=data["missing_xml_count"],
        xml_mismatch_count=data["xml_mismatch_count"],
        invalid_access_key_count=data["invalid_access_key_count"],
        quarantined_item_count=data["quarantined_item_count"],
    )


@analytics_router.get("/freshness", response_model=FuelPurchasesFreshnessResponse)
async def purchases_freshness(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchasesFreshnessResponse:
    _ensure(user, Permission.FUEL_PURCHASES_READ)
    data = await FuelPurchasesAnalyticsService(db).freshness(organization_id=user.organization_id)
    return FuelPurchasesFreshnessResponse(**data)


@invoices_router.get("", response_model=PaginatedInvoices)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    station_ids: list[uuid.UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> PaginatedInvoices:
    _ensure(user, Permission.PURCHASE_INVOICES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, station_ids)
    rows, total = await FuelPurchasesAnalyticsService(db).list_invoices(
        organization_id=user.organization_id,
        station_ids=stations,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    return PaginatedInvoices(
        items=[
            FuelPurchaseInvoiceListRow(
                id=r["id"],
                station_id=r["station_id"],
                station_name=r["station_name"],
                source_document_number=r["source_document_number"],
                source_series=r["source_series"],
                access_key=r["access_key"],
                entry_date=r["entry_date"],
                issue_date=r["issue_date"],
                distributor_name=r["distributor_name"],
                purchased_volume_liters=_dec(r["purchased_volume_liters"]) or "0",
                total_amount=_dec(r["total_amount"]) or "0",
                delivered_cost_per_liter=_dec(r.get("delivered_cost_per_liter")),
                has_xml=r["has_xml"],
                xml_imported_in_erp=r.get("xml_imported_in_erp", False),
                xml_reconciliation_status=r["xml_reconciliation_status"],
                metric_eligibility_status=r["metric_eligibility_status"],
                is_cancelled=r["is_cancelled"],
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@invoices_router.get("/{invoice_id}", response_model=FuelPurchaseInvoiceDetail)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchaseInvoiceDetail:
    _ensure(user, Permission.PURCHASE_INVOICES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    data = await FuelPurchasesAnalyticsService(db).invoice_detail(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=invoice_id,
    )
    if data is None:
        raise AppError("Nota não encontrada.", status_code=404, code="NOT_FOUND")
    return FuelPurchaseInvoiceDetail(
        id=data["id"],
        station_id=data["station_id"],
        station_name=data["station_name"],
        source_invoice_id=data["source_invoice_id"],
        source_document_number=data["source_document_number"],
        source_series=data["source_series"],
        access_key=data["access_key"],
        xml_imported_in_erp=bool(data.get("xml_imported_in_erp")),
        has_xml_file=bool(data.get("has_xml_file")),
        distributor_id=data["distributor_id"],
        distributor_name=data["distributor_name"],
        source_supplier_id=data["source_supplier_id"],
        issue_date=data["issue_date"],
        entry_date=data["entry_date"],
        operation_type=data["operation_type"],
        source_status=data["source_status"],
        is_cancelled=data["is_cancelled"],
        gross_amount=_dec(data["gross_amount"]) or "0",
        discount_amount=_dec(data["discount_amount"]) or "0",
        freight_amount=_dec(data["freight_amount"]) or "0",
        insurance_amount=_dec(data["insurance_amount"]) or "0",
        other_expenses_amount=_dec(data["other_expenses_amount"]) or "0",
        tax_amount=_dec(data["tax_amount"]) or "0",
        total_amount=_dec(data["total_amount"]) or "0",
        purchased_volume_liters=_dec(data["purchased_volume_liters"]) or "0",
        commercial_delivered_cost=_dec(data["commercial_delivered_cost"]) or "0",
        average_delivered_cost_per_liter=_dec(data.get("average_delivered_cost_per_liter")),
        allocation_method=data["allocation_method"],
        metric_eligibility_status=data["metric_eligibility_status"],
        metric_exclusion_reasons=data["metric_exclusion_reasons"],
        payment_condition_id=data["payment_condition_id"],
    )


@invoices_router.get("/{invoice_id}/items", response_model=list[FuelPurchaseInvoiceItemRow])
async def get_invoice_items(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchaseInvoiceItemRow]:
    _ensure(user, Permission.PURCHASE_INVOICES_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    rows = await FuelPurchasesAnalyticsService(db).invoice_items(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=invoice_id,
    )
    return [
        FuelPurchaseInvoiceItemRow(
            id=r["id"],
            source_description=r["source_description"],
            product_name=r["product_name"],
            source_product_id=r["source_product_id"],
            volume_liters=_dec(r["volume_liters"]),
            source_quantity=_dec(r["source_quantity"]) or "0",
            source_unit=r["source_unit"],
            unit_price=_dec(r["unit_price"]) or "0",
            gross_item_amount=_dec(r["gross_item_amount"]) or "0",
            discount_amount=_dec(r["discount_amount"]) or "0",
            allocated_freight_amount=_dec(r["allocated_freight_amount"]) or "0",
            allocated_insurance_amount=_dec(r["allocated_insurance_amount"]) or "0",
            allocated_other_expenses=_dec(r["allocated_other_expenses"]) or "0",
            commercial_delivered_cost=_dec(r["commercial_delivered_cost"]) or "0",
            delivered_cost_per_liter=_dec(r.get("delivered_cost_per_liter")),
            erp_recorded_cost=_dec(r.get("erp_recorded_cost")),
            accounting_cost=_dec(r.get("accounting_cost")),
            icms_amount=_dec(r.get("icms_amount")),
            icms_st_amount=_dec(r.get("icms_st_amount")),
            fcp_amount=_dec(r.get("fcp_amount")),
            pis_amount=_dec(r.get("pis_amount")),
            cofins_amount=_dec(r.get("cofins_amount")),
            cfop=r["cfop"],
            ncm=r["ncm"],
            metric_eligibility_status=r["metric_eligibility_status"],
            metric_exclusion_reasons=r["metric_exclusion_reasons"],
        )
        for r in rows
    ]


@invoices_router.get("/{invoice_id}/titles", response_model=list[FuelPurchaseInvoiceTitleRow])
async def get_invoice_titles(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[FuelPurchaseInvoiceTitleRow]:
    _ensure(user, Permission.ACCOUNTS_PAYABLE_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    rows = await FuelPurchasesAnalyticsService(db).invoice_titles(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=invoice_id,
    )
    return [
        FuelPurchaseInvoiceTitleRow(
            id=r["id"],
            installment_number=r["installment_number"],
            document_number=r["document_number"],
            due_date=r["due_date"],
            payment_date=r["payment_date"],
            original_amount=_dec(r["original_amount"]) or "0",
            paid_amount=_dec(r.get("paid_amount")),
            open_amount=_dec(r["open_amount"]) or "0",
            normalized_status=r["normalized_status"],
            source_status=r["source_status"],
        )
        for r in rows
    ]


@invoices_router.get("/{invoice_id}/xml", response_model=FuelPurchaseInvoiceXmlInfo)
async def get_invoice_xml(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> FuelPurchaseInvoiceXmlInfo:
    _ensure(user, Permission.PURCHASE_INVOICES_VIEW_XML)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    data = await FuelPurchasesAnalyticsService(db).invoice_xml(
        organization_id=user.organization_id,
        station_ids=stations,
        invoice_id=invoice_id,
    )
    return FuelPurchaseInvoiceXmlInfo(**data)


@ap_router.get("/summary", response_model=AccountsPayableSummaryResponse)
async def ap_summary(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> AccountsPayableSummaryResponse:
    _ensure(user, Permission.ACCOUNTS_PAYABLE_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    data = await FuelPurchasesAnalyticsService(db).ap_summary(
        organization_id=user.organization_id,
        station_ids=stations,
    )
    hide = Permission.ACCOUNTS_PAYABLE_VIEW_VALUES.value not in user.permissions
    return AccountsPayableSummaryResponse(
        open_amount="***" if hide else (_dec(data["open_amount"]) or "0"),
        overdue_amount="***" if hide else (_dec(data["overdue_amount"]) or "0"),
        due_in_7_days_amount="***" if hide else (_dec(data["due_in_7_days_amount"]) or "0"),
        due_in_30_days_amount="***" if hide else (_dec(data["due_in_30_days_amount"]) or "0"),
        weighted_term_days=_dec(data.get("weighted_term_days")),
        partially_paid_count=data["partially_paid_count"],
        open_title_count=data["open_title_count"],
    )


@ap_router.get("/aging", response_model=list[AccountsPayableAgingBucket])
async def ap_aging(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> list[AccountsPayableAgingBucket]:
    _ensure(user, Permission.ACCOUNTS_PAYABLE_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    rows = await FuelPurchasesAnalyticsService(db).ap_aging(
        organization_id=user.organization_id,
        station_ids=stations,
    )
    hide = Permission.ACCOUNTS_PAYABLE_VIEW_VALUES.value not in user.permissions
    return [
        AccountsPayableAgingBucket(
            bucket=r["bucket"],
            title_count=r["title_count"],
            open_amount="***" if hide else (_dec(r["open_amount"]) or "0"),
        )
        for r in rows
    ]


@ap_router.get("/titles", response_model=PaginatedTitles)
async def ap_titles(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> PaginatedTitles:
    _ensure(user, Permission.ACCOUNTS_PAYABLE_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    rows, total = await FuelPurchasesAnalyticsService(db).list_titles(
        organization_id=user.organization_id,
        station_ids=stations,
        page=page,
        page_size=page_size,
        status=status,
    )
    hide = Permission.ACCOUNTS_PAYABLE_VIEW_VALUES.value not in user.permissions
    return PaginatedTitles(
        items=[
            AccountsPayableTitleListRow(
                id=r["id"],
                station_id=r["station_id"],
                station_name=r["station_name"],
                distributor_name=r["distributor_name"],
                document_number=r["document_number"],
                installment_number=r["installment_number"],
                due_date=r["due_date"],
                payment_date=r["payment_date"],
                original_amount="***" if hide else (_dec(r["original_amount"]) or "0"),
                paid_amount=None if hide else _dec(r.get("paid_amount")),
                open_amount="***" if hide else (_dec(r["open_amount"]) or "0"),
                normalized_status=r["normalized_status"],
                purchase_invoice_id=r["purchase_invoice_id"],
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@nfe_router.get("", response_model=PaginatedNfeDocuments)
async def list_nfe(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> PaginatedNfeDocuments:
    _ensure(user, Permission.NFE_DOCUMENTS_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    rows, total = await FuelPurchasesAnalyticsService(db).list_nfe(
        organization_id=user.organization_id,
        station_ids=stations,
        page=page,
        page_size=page_size,
        q=q,
    )
    return PaginatedNfeDocuments(
        items=[
            NfeDocumentRow(
                id=r["id"],
                station_id=r["station_id"],
                station_name=r["station_name"],
                access_key=r["access_key"],
                document_number=r["document_number"],
                series=r["series"],
                issuer_cnpj=r["issuer_cnpj"],
                issue_datetime=r["issue_datetime"],
                total_amount=_dec(r["total_amount"]) or "0",
                parse_status=r["parse_status"],
                reconciliation_status=r["reconciliation_status"],
                purchase_invoice_id=r["purchase_invoice_id"],
                xml_size_bytes=r["xml_size_bytes"],
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@nfe_router.get("/{doc_id}", response_model=NfeDocumentDetail)
async def get_nfe(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_active_user),
) -> NfeDocumentDetail:
    _ensure(user, Permission.NFE_DOCUMENTS_READ)
    stations = await _resolve_station_ids(AuthService(db), user, None)
    data = await FuelPurchasesAnalyticsService(db).nfe_detail(
        organization_id=user.organization_id,
        station_ids=stations,
        doc_id=doc_id,
    )
    if data is None:
        raise AppError("Documento NF-e não encontrado.", status_code=404, code="NOT_FOUND")
    return NfeDocumentDetail(
        id=data["id"],
        station_id=data["station_id"],
        station_name=data["station_name"],
        access_key=data["access_key"],
        document_number=data["document_number"],
        series=data["series"],
        issuer_cnpj=data["issuer_cnpj"],
        recipient_cnpj=data["recipient_cnpj"],
        issue_datetime=data["issue_datetime"],
        total_amount=_dec(data["total_amount"]) or "0",
        parse_status=data["parse_status"],
        reconciliation_status=data["reconciliation_status"],
        purchase_invoice_id=data["purchase_invoice_id"],
        xml_size_bytes=data["xml_size_bytes"],
        parse_errors=data["parse_errors"],
        reconciliation_details=data["reconciliation_details"],
        imported_at=data["imported_at"],
    )
