from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    distribution_bases,
    distributors,
    erp_products,
    erp_suppliers,
    financial_parameters,
    health,
    master_data_imports,
    organization_business_settings,
    organizations,
    payment_terms,
    products,
    quote_comparisons,
    quotes,
    stations,
    supplier_rules,
    users,
    xpert_integration,
    fuel_sales_analytics,
    erp_payment_methods,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(organization_business_settings.router)
api_router.include_router(stations.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(products.router)
api_router.include_router(erp_products.router)
api_router.include_router(distributors.router)
api_router.include_router(distribution_bases.router)
api_router.include_router(erp_suppliers.router)
api_router.include_router(payment_terms.router)
api_router.include_router(supplier_rules.router)
api_router.include_router(quotes.router)
api_router.include_router(financial_parameters.router)
api_router.include_router(quote_comparisons.router)
api_router.include_router(master_data_imports.router)
api_router.include_router(xpert_integration.router)
api_router.include_router(fuel_sales_analytics.router)
api_router.include_router(erp_payment_methods.router)
