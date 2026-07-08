import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.erp_product import ErpProduct
from app.models.product import Product
from app.seeds.master_data import VALID_COMMERCIAL_VARIANTS, VALID_FUEL_FAMILIES
from app.services.audit_service import AuditContext, AuditService


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def list_products(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None = None,
        fuel_family: str | None = None,
        commercial_variant: str | None = None,
        active: bool | None = None,
        purchasable: bool | None = None,
        sellable: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        query = select(Product).where(Product.organization_id == organization_id)
        if search:
            term = f"%{search}%"
            query = query.where(or_(Product.code.ilike(term), Product.name.ilike(term)))
        if fuel_family:
            query = query.where(Product.fuel_family == fuel_family)
        if commercial_variant:
            query = query.where(Product.commercial_variant == commercial_variant)
        if active is not None:
            query = query.where(Product.active.is_(active))
        if purchasable is not None:
            query = query.where(Product.purchasable.is_(purchasable))
        if sellable is not None:
            query = query.where(Product.sellable.is_(sellable))

        count_q = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = (
            query.order_by(Product.display_order, Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, product_id: uuid.UUID, organization_id: uuid.UUID) -> Product:
        product = await self.db.get(Product, product_id)
        if product is None or product.organization_id != organization_id:
            raise AppError("Produto não encontrado.", status_code=404, code="NOT_FOUND")
        return product

    def _validate_fuel_classification(self, fuel_family: str, commercial_variant: str) -> None:
        if fuel_family not in VALID_FUEL_FAMILIES:
            raise AppError(
                "Família de combustível inválida.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        if commercial_variant not in VALID_COMMERCIAL_VARIANTS:
            raise AppError(
                "Variante comercial inválida.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

    async def _ensure_code_unique(
        self, organization_id: uuid.UUID, code: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(Product).where(Product.organization_id == organization_id, Product.code == code)
        if exclude_id:
            query = query.where(Product.id != exclude_id)
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise AppError(
                "Já existe um produto com este código.",
                status_code=409,
                code="PRODUCT_CODE_ALREADY_EXISTS",
            )

    async def _is_product_in_use(self, product_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(ErpProduct.id).where(ErpProduct.canonical_product_id == product_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def create(self, *, organization_id: uuid.UUID, data: dict, audit_ctx: AuditContext) -> Product:
        code = str(data["code"]).strip().upper()
        if not code:
            raise AppError("Código do produto é obrigatório.", status_code=400, code="VALIDATION_ERROR")
        name = str(data["name"]).strip()
        if not name:
            raise AppError("Nome do produto é obrigatório.", status_code=400, code="VALIDATION_ERROR")

        fuel_family = data["fuel_family"]
        commercial_variant = data["commercial_variant"]
        self._validate_fuel_classification(fuel_family, commercial_variant)
        await self._ensure_code_unique(organization_id, code)

        product = Product(
            organization_id=organization_id,
            code=code,
            name=name,
            fuel_family=fuel_family,
            commercial_variant=commercial_variant,
            unit=data.get("unit", "LITER"),
            regulatory_code=data.get("regulatory_code"),
            purchasable=data.get("purchasable", True),
            sellable=data.get("sellable", True),
            display_order=data.get("display_order", 0),
            active=data.get("active", True),
        )
        self.db.add(product)
        await self.db.flush()
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="product",
            entity_id=product.id,
            action="create",
            after_data=self._serialize(product),
        )
        return product

    async def update(
        self, *, product: Product, data: dict, audit_ctx: AuditContext
    ) -> Product:
        before = self._serialize(product)

        if "code" in data:
            new_code = str(data["code"]).strip().upper()
            if new_code != product.code:
                if product.code_locked or await self._is_product_in_use(product.id):
                    raise AppError(
                        "O código não pode ser alterado porque o produto já está em uso.",
                        status_code=409,
                        code="PRODUCT_IN_USE",
                    )
                await self._ensure_code_unique(product.organization_id, new_code, exclude_id=product.id)
                product.code = new_code

        if "name" in data:
            name = str(data["name"]).strip()
            if not name:
                raise AppError("Nome do produto é obrigatório.", status_code=400, code="VALIDATION_ERROR")
            product.name = name

        fuel_family = data.get("fuel_family", product.fuel_family)
        commercial_variant = data.get("commercial_variant", product.commercial_variant)
        if "fuel_family" in data or "commercial_variant" in data:
            self._validate_fuel_classification(fuel_family, commercial_variant)
            product.fuel_family = fuel_family
            product.commercial_variant = commercial_variant

        for field in (
            "unit",
            "regulatory_code",
            "purchasable",
            "sellable",
            "display_order",
            "active",
        ):
            if field in data:
                setattr(product, field, data[field])

        product.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="product",
            entity_id=product.id,
            action="update",
            before_data=before,
            after_data=self._serialize(product),
        )
        return product

    async def deactivate(
        self, *, product: Product, reason: str, audit_ctx: AuditContext
    ) -> Product:
        before = self._serialize(product)
        product.active = False
        product.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="product",
            entity_id=product.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize(product),
            metadata={"reason": reason},
        )
        return product

    async def reactivate(self, *, product: Product, audit_ctx: AuditContext) -> Product:
        before = self._serialize(product)
        product.active = True
        product.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="product",
            entity_id=product.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize(product),
        )
        return product

    async def lock_code_if_used(self, product: Product) -> None:
        if not product.code_locked:
            product.code_locked = True
            product.updated_at = datetime.now(UTC)

    def _serialize(self, product: Product) -> dict:
        return {
            "id": str(product.id),
            "organization_id": str(product.organization_id),
            "code": product.code,
            "name": product.name,
            "fuel_family": product.fuel_family,
            "commercial_variant": product.commercial_variant,
            "unit": product.unit,
            "regulatory_code": product.regulatory_code,
            "purchasable": product.purchasable,
            "sellable": product.sellable,
            "display_order": product.display_order,
            "active": product.active,
            "code_locked": product.code_locked,
        }
