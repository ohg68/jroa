from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Catalog(Base):
    __tablename__ = "catalogs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    optimized_path = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, processing, processed, error
    total_pages = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    optimized_size = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    products = relationship("Product", back_populates="catalog", cascade="all, delete-orphan")

    @property
    def total_products(self):
        return len(self.products)

    @property
    def valid_products(self):
        return sum(1 for p in self.products if not p.needs_review)

    @property
    def review_products(self):
        return sum(1 for p in self.products if p.needs_review)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    name = Column(String, nullable=False)
    default_code = Column(String, nullable=True)  # SKU / reference
    list_price = Column(Float, nullable=True)
    categ_id = Column(String, nullable=True)  # category path for Odoo
    description_sale = Column(Text, nullable=True)
    brand = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    needs_review = Column(Boolean, default=False)
    review_reason = Column(String, nullable=True)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    catalog = relationship("Catalog", back_populates="products")
