from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductResponse, ProductUpdate

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", response_model=list[ProductResponse])
def list_products(
    catalog_id: int | None = None,
    needs_review: bool | None = None,
    missing_price: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if catalog_id is not None:
        query = query.filter(Product.catalog_id == catalog_id)

    if needs_review is not None:
        query = query.filter(Product.needs_review == needs_review)

    if missing_price:
        query = query.filter(
            (Product.list_price == None) | (Product.list_price <= 0)  # noqa: E711
        )

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
            | Product.default_code.ilike(f"%{search}%")
            | Product.brand.ilike(f"%{search}%")
        )

    total = query.count()
    products = (
        query.order_by(Product.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return products


@router.get("/count")
def count_products(
    catalog_id: int | None = None,
    needs_review: bool | None = None,
    missing_price: bool | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if catalog_id is not None:
        query = query.filter(Product.catalog_id == catalog_id)
    if needs_review is not None:
        query = query.filter(Product.needs_review == needs_review)
    if missing_price:
        query = query.filter(
            (Product.list_price == None) | (Product.list_price <= 0)  # noqa: E711
        )

    return {"count": query.count()}


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    update: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    # Recalculate needs_review if relevant fields changed
    if "list_price" in update_data or "default_code" in update_data:
        review_reasons = []
        if product.list_price is None or product.list_price <= 0:
            review_reasons.append("missing_price")
        if not product.default_code:
            review_reasons.append("missing_sku")

        if "needs_review" not in update_data:
            product.needs_review = len(review_reasons) > 0
            product.review_reason = ", ".join(review_reasons) if review_reasons else None

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}
