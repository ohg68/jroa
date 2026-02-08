from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.database import get_db
from app.models import Product, Catalog
from app.services.csv_service import products_to_csv

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def export_all_csv(
    needs_review: bool | None = None,
    missing_price: bool | None = None,
    db: Session = Depends(get_db),
):
    """Export all products as Odoo-compatible CSV."""
    query = db.query(Product)

    if needs_review is not None:
        query = query.filter(Product.needs_review == needs_review)
    if missing_price:
        query = query.filter(
            (Product.list_price == None) | (Product.list_price <= 0)  # noqa: E711
        )

    products = query.order_by(Product.id).all()

    if not products:
        raise HTTPException(status_code=404, detail="No products to export")

    csv_content = products_to_csv(products)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_odoo.csv"},
    )


@router.get("/csv/{catalog_id}")
def export_catalog_csv(catalog_id: int, db: Session = Depends(get_db)):
    """Export products from a specific catalog as Odoo-compatible CSV."""
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    products = (
        db.query(Product)
        .filter(Product.catalog_id == catalog_id)
        .order_by(Product.id)
        .all()
    )

    if not products:
        raise HTTPException(status_code=404, detail="No products in this catalog")

    csv_content = products_to_csv(products)
    safe_name = catalog.filename.replace(".pdf", "").replace(" ", "_")

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}_odoo.csv"
        },
    )
