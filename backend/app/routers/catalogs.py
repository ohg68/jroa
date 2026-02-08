import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Catalog, Product
from app.schemas import CatalogResponse, DashboardResponse
from app.services import pdf_service, ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


def _process_catalog(catalog_id: int, db_factory):
    """Background task to process a catalog with AI extraction."""
    db = db_factory()
    try:
        catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
        if not catalog:
            return

        catalog.status = "processing"
        db.commit()

        try:
            # First try text extraction
            pdf_path = catalog.optimized_path or catalog.original_path
            pages_text = pdf_service.extract_text_from_pdf(pdf_path)

            # Check if we have meaningful text content
            total_text = "".join(pages_text).strip()
            if len(total_text) < 50:
                # Fallback to vision-based extraction for scanned PDFs
                logger.info(f"Catalog {catalog_id}: Low text content, using vision extraction")
                page_images = pdf_service.extract_pages_as_images(pdf_path)
                raw_products = ai_service.extract_products_from_images(page_images)
            else:
                raw_products = ai_service.extract_products_from_text(pages_text)

            # Delete existing products for reprocessing
            db.query(Product).filter(Product.catalog_id == catalog_id).delete()

            # Create product records
            for raw in raw_products:
                name = raw.get("name", "").strip()
                if not name:
                    continue

                price = raw.get("list_price")
                if price is not None:
                    try:
                        price = float(price)
                    except (ValueError, TypeError):
                        price = None

                needs_review = False
                review_reasons = []

                if price is None or price <= 0:
                    needs_review = True
                    review_reasons.append("missing_price")

                if not raw.get("default_code"):
                    needs_review = True
                    review_reasons.append("missing_sku")

                product = Product(
                    catalog_id=catalog_id,
                    name=name,
                    default_code=raw.get("default_code"),
                    list_price=price,
                    categ_id=raw.get("categ_id"),
                    description_sale=raw.get("description_sale"),
                    brand=raw.get("brand"),
                    unit=raw.get("unit"),
                    needs_review=needs_review,
                    review_reason=", ".join(review_reasons) if review_reasons else None,
                    page_number=raw.get("page_number"),
                )
                db.add(product)

            catalog.status = "processed"
            catalog.processed_at = datetime.now(timezone.utc)
            catalog.error_message = None
            db.commit()
            logger.info(f"Catalog {catalog_id}: Extracted {len(raw_products)} products")

        except Exception as e:
            catalog.status = "error"
            catalog.error_message = str(e)[:500]
            db.commit()
            logger.error(f"Catalog {catalog_id} processing error: {e}")

    finally:
        db.close()


@router.post("/upload", response_model=CatalogResponse)
async def upload_catalog(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")

    path = pdf_service.save_upload(file.filename, content)
    info = pdf_service.get_pdf_info(path)

    catalog = Catalog(
        filename=file.filename,
        original_path=path,
        status="pending",
        total_pages=info["total_pages"],
        file_size=info["file_size"],
    )
    db.add(catalog)
    db.commit()
    db.refresh(catalog)

    # Start processing in background
    from app.database import SessionLocal
    background_tasks.add_task(_process_catalog, catalog.id, SessionLocal)

    return catalog


@router.get("/", response_model=list[CatalogResponse])
def list_catalogs(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Catalog)
    if status:
        query = query.filter(Catalog.status == status)
    return query.order_by(Catalog.created_at.desc()).all()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    catalogs = db.query(Catalog).all()
    products = db.query(Product).all()

    return DashboardResponse(
        total_catalogs=len(catalogs),
        processed_catalogs=sum(1 for c in catalogs if c.status == "processed"),
        pending_catalogs=sum(1 for c in catalogs if c.status in ("pending", "processing")),
        error_catalogs=sum(1 for c in catalogs if c.status == "error"),
        total_products=len(products),
        valid_products=sum(1 for p in products if not p.needs_review),
        review_products=sum(1 for p in products if p.needs_review),
    )


@router.get("/{catalog_id}", response_model=CatalogResponse)
def get_catalog(catalog_id: int, db: Session = Depends(get_db)):
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog


@router.post("/{catalog_id}/reprocess")
async def reprocess_catalog(
    catalog_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    catalog.status = "pending"
    db.commit()

    from app.database import SessionLocal
    background_tasks.add_task(_process_catalog, catalog.id, SessionLocal)

    return {"message": "Reprocessing started"}


@router.post("/{catalog_id}/optimize")
def optimize_catalog(catalog_id: int, db: Session = Depends(get_db)):
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    try:
        optimized_path = pdf_service.optimize_pdf(catalog.original_path)
        catalog.optimized_path = optimized_path
        catalog.optimized_size = os.path.getsize(optimized_path)
        db.commit()
        db.refresh(catalog)
        return {
            "message": "PDF optimized",
            "original_size": catalog.file_size,
            "optimized_size": catalog.optimized_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.delete("/{catalog_id}")
def delete_catalog(catalog_id: int, db: Session = Depends(get_db)):
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")

    # Clean up files
    for path in [catalog.original_path, catalog.optimized_path]:
        if path and os.path.exists(path):
            os.remove(path)

    db.delete(catalog)
    db.commit()
    return {"message": "Catalog deleted"}


@router.delete("/")
def delete_all_catalogs(db: Session = Depends(get_db)):
    catalogs = db.query(Catalog).all()
    for catalog in catalogs:
        for path in [catalog.original_path, catalog.optimized_path]:
            if path and os.path.exists(path):
                os.remove(path)
    db.query(Product).delete()
    db.query(Catalog).delete()
    db.commit()
    return {"message": "All catalogs deleted"}
