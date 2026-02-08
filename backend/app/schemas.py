from datetime import datetime
from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    default_code: str | None = None
    list_price: float | None = None
    categ_id: str | None = None
    description_sale: str | None = None
    brand: str | None = None
    unit: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    default_code: str | None = None
    list_price: float | None = None
    categ_id: str | None = None
    description_sale: str | None = None
    brand: str | None = None
    unit: str | None = None
    needs_review: bool | None = None
    review_reason: str | None = None


class ProductResponse(ProductBase):
    id: int
    catalog_id: int
    needs_review: bool
    review_reason: str | None
    page_number: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CatalogResponse(BaseModel):
    id: int
    filename: str
    status: str
    total_pages: int
    file_size: int
    optimized_size: int | None
    error_message: str | None
    total_products: int
    valid_products: int
    review_products: int
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    total_catalogs: int
    processed_catalogs: int
    pending_catalogs: int
    error_catalogs: int
    total_products: int
    valid_products: int
    review_products: int
