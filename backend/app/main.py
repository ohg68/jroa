import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import catalogs, products, export

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PDF Catalog Extractor",
    description="Extract products from PDF catalogs using AI and export to Odoo-compatible CSV",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogs.router)
app.include_router(products.router)
app.include_router(export.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
